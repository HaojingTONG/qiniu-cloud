#!/usr/bin/env python3
"""
Voice-activated macOS assistant CLI.
Main entry point for the application.
支持单步 Intent 和多步 Plan 执行。(Supports single-step Intent and multi-step Plan execution)
"""
import sys
from pathlib import Path
from typing import Optional, Union

import typer
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.schema import Intent, Plan
from app.planner import create_planner
from app.executor import create_executor
from app.tts import create_tts_engine
from app.verbalizer import create_verbalizer
from app.utils import logger
from app.eventbus import get_event_bus, EventType
from app.webui import create_webui_server


app = typer.Typer(help="Voice-activated macOS assistant")
console = Console()


def get_user_confirmation(message: str, use_ui: bool = False) -> bool:
    """
    Get user confirmation via terminal or Web UI.

    Args:
        message: Confirmation message to display
        use_ui: If True, use Web UI confirmation; otherwise use terminal

    Returns:
        True if confirmed, False if cancelled
    """
    if use_ui:
        # Use Web UI confirmation
        event_bus = get_event_bus()

        # Publish confirmation required event
        event_bus.publish(EventType.CONFIRMATION_REQUIRED, {
            "message": message
        })

        # Wait for user response from Web UI
        confirmed = event_bus.wait_for_confirmation(timeout=300.0)
        return confirmed
    else:
        # Use terminal confirmation
        return typer.confirm(message, default=False)


def create_asr_engine_from_config():
    """Create ASR engine based on configuration."""
    asr_engine = config.ASR_ENGINE.lower()

    if asr_engine == "macos":
        try:
            from app.asr_macos import create_asr_engine
            logger.info("Using macOS native speech recognition")
            return create_asr_engine(language=config.ASR_LANGUAGE)
        except ImportError as e:
            logger.error(f"Failed to import macOS ASR: {e}")
            console.print("[yellow]⚠️  Falling back to text input mode[/yellow]")
            from app.asr import create_asr_engine
            return create_asr_engine()
    elif asr_engine == "text":
        from app.asr import create_asr_engine
        logger.info("Using text input mode")
        return create_asr_engine()
    else:
        logger.warning(f"Unknown ASR engine: {asr_engine}, using text input")
        from app.asr import create_asr_engine
        return create_asr_engine()


def process_utterance(
    text: str,
    planner,
    executor,
    verbalizer,
    tts,
    dry_run: bool = False,
    plan_debug: bool = False,
    use_ui: bool = False
) -> bool:
    """
    处理单条用户输入，支持单步 Intent 或多步 Plan。
    (Process a single user utterance, supports both single Intent and multi-step Plan)

    Args:
        text: User utterance
        planner: Planner instance
        executor: Executor instance
        verbalizer: Verbalizer instance
        tts: TTS engine instance
        dry_run: If True, only show what would be executed
        plan_debug: If True, show plan but don't execute

    Returns:
        True to continue, False to exit
    """
    # Check for exit commands
    if text.lower() in ["exit", "quit", "退出", "拜拜", "再见"]:
        tts.speak("再见！")
        return False

    try:
        # Publish planning start event
        if use_ui:
            event_bus = get_event_bus()
            event_bus.publish(EventType.PLANNING_START, {"text": text})

        # Parse plan or intent
        console.print(f"\n[cyan]📝 Planning...[/cyan]")
        result = planner.parse_plan_or_intent(text, dry_run=dry_run or plan_debug)

        # Publish plan/intent parsed event
        if use_ui:
            event_bus = get_event_bus()
            if isinstance(result, Plan):
                event_bus.publish(EventType.PLAN_PARSED, {
                    "summary": result.summary,
                    "steps": [{"intent": step.intent, "slots": step.slots} for step in result.plan],
                    "total": len(result.plan)
                })

        # Check if it's a Plan or Intent
        if isinstance(result, Plan):
            return process_plan(result, executor, verbalizer, tts, dry_run, plan_debug, use_ui)
        else:
            return process_intent(result, executor, verbalizer, tts, dry_run, use_ui)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error processing utterance: {e}")
        console.print(f"[bold red]Error:[/bold red] {e}")
        tts.speak("抱歉，出错了")
        return True


def process_intent(
    intent: Intent,
    executor,
    verbalizer,
    tts,
    dry_run: bool = False,
    use_ui: bool = False
) -> bool:
    """
    处理单步 Intent（原有逻辑）。
    (Process a single Intent - original logic)
    """
    # Publish intent parsed event
    if use_ui:
        event_bus = get_event_bus()
        event_bus.publish(EventType.INTENT_PARSED, {
            "intent": intent.intent,
            "slots": intent.slots,
            "safety": intent.safety
        })

    # Display intent
    console.print(Panel(
        f"[bold]Intent:[/bold] {intent.intent}\n"
        f"[bold]Slots:[/bold] {intent.slots}\n"
        f"[bold]Confirm:[/bold] {intent.confirm}\n"
        f"[bold]Safety:[/bold] {intent.safety}",
        title="🎯 Parsed Intent",
        border_style="green"
    ))

    # Confirmation if needed
    if intent.confirm:
        confirmation = verbalizer.generate_confirmation(intent)
        tts.speak(confirmation)

        if not dry_run:
            response = get_user_confirmation("继续执行？", use_ui=use_ui)
            if not response:
                tts.speak("已取消")
                return True

    # Generate and speak confirmation
    if not intent.confirm:
        confirmation = verbalizer.generate_confirmation(intent)
        tts.speak(confirmation)

    # Execute
    if dry_run:
        msg = verbalizer.generate_dry_run_message(intent)
        console.print(f"\n[yellow]{msg}[/yellow]")
    else:
        console.print(f"\n[cyan]⚙️  Executing...[/cyan]")
        result = executor.execute(intent)

        # Display result
        if result.success:
            console.print(Panel(
                f"[bold green]✓ Success[/bold green]\n{result.message}",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[bold red]✗ Failed[/bold red]\n{result.message}\n[dim]{result.error}[/dim]",
                border_style="red"
            ))

        # Publish intent complete event
        if use_ui:
            event_bus = get_event_bus()
            event_data = {
                "intent": intent.intent,
                "success": result.success,
                "message": result.message
            }
            # Include file path if available
            if result.file_path:
                event_data["file_path"] = result.file_path
            event_bus.publish(EventType.INTENT_COMPLETE, event_data)

        # Speak result
        result_msg = verbalizer.generate_result_message(intent, result)

        # Publish TTS event
        if use_ui:
            event_bus.publish(EventType.TTS_START, {"text": result_msg})

        tts.speak(result_msg)

    return True


def process_plan(
    plan: Plan,
    executor,
    verbalizer,
    tts,
    dry_run: bool = False,
    plan_debug: bool = False,
    use_ui: bool = False
) -> bool:
    """
    处理多步 Plan，顺序执行，失败即停。
    (Process multi-step Plan, execute sequentially, stop on first failure)
    """
    # Get event bus if UI is enabled
    if use_ui:
        event_bus = get_event_bus()

    # Display plan overview
    plan_steps = "\n".join([
        f"  {i+1}. [{step.intent}] {step.slots}"
        for i, step in enumerate(plan.plan)
    ])

    console.print(Panel(
        f"[bold]Plan Summary:[/bold] {plan.summary}\n"
        f"[bold]Total Steps:[/bold] {len(plan.plan)}\n\n"
        f"[bold]Steps:[/bold]\n{plan_steps}",
        title="🗂️  Multi-Step Plan",
        border_style="blue"
    ))

    # If plan_debug, just show and return
    if plan_debug:
        console.print("\n[yellow]📋 Plan debug mode: showing plan only, not executing[/yellow]")
        return True

    # Check for dangerous steps
    has_dangerous = any(step.confirm or step.safety.get("risk") == "high" for step in plan.plan)

    if has_dangerous:
        plan_msg = f"这个计划包含{len(plan.plan)}个步骤，其中有需要确认的操作"
        if use_ui:
            event_bus.publish(EventType.TTS_START, {"text": plan_msg})
        tts.speak(plan_msg)

        if not dry_run:
            response = get_user_confirmation("是否执行整个计划？", use_ui=use_ui)
            if not response:
                cancel_msg = "已取消"
                if use_ui:
                    event_bus.publish(EventType.TTS_START, {"text": cancel_msg})
                tts.speak(cancel_msg)
                return True
    else:
        start_msg = f"好的，开始执行{len(plan.plan)}个步骤"
        if use_ui:
            event_bus.publish(EventType.TTS_START, {"text": start_msg})
        tts.speak(start_msg)

    # Execute each step sequentially
    for i, intent in enumerate(plan.plan):
        console.print(f"\n[cyan]📍 Step {i+1}/{len(plan.plan)}: {intent.intent}[/cyan]")

        # Publish step start event
        if use_ui:
            event_bus.publish(EventType.STEP_START, {
                "step_number": i + 1,
                "intent": intent.intent,
                "slots": intent.slots
            })

        # Display step intent
        console.print(Panel(
            f"[bold]Intent:[/bold] {intent.intent}\n"
            f"[bold]Slots:[/bold] {intent.slots}\n"
            f"[bold]Safety:[/bold] {intent.safety}",
            title=f"Step {i+1}",
            border_style="cyan"
        ))

        # Step-level confirmation if needed
        if intent.confirm and not dry_run:
            confirmation = verbalizer.generate_confirmation(intent)
            tts.speak(confirmation)
            response = get_user_confirmation(f"继续执行步骤 {i+1}？", use_ui=use_ui)
            if not response:
                tts.speak("计划已中止")
                console.print(f"\n[yellow]⚠️  Plan aborted at step {i+1}[/yellow]")
                return True

        # Execute step
        if dry_run:
            msg = verbalizer.generate_dry_run_message(intent)
            console.print(f"   [yellow]{msg}[/yellow]")
        else:
            result = executor.execute(intent)

            # Display result
            if result.success:
                console.print(f"   [green]✓ Step {i+1} completed[/green]")

                # Publish step complete event
                if use_ui:
                    event_data = {
                        "step_number": i + 1,
                        "message": result.message
                    }
                    # Include file path if available
                    if result.file_path:
                        event_data["file_path"] = result.file_path
                    event_bus.publish(EventType.STEP_COMPLETE, event_data)
            else:
                console.print(Panel(
                    f"[bold red]✗ Step {i+1} Failed[/bold red]\n{result.message}\n[dim]{result.error}[/dim]",
                    border_style="red"
                ))

                # Publish step error event
                if use_ui:
                    event_bus.publish(EventType.STEP_ERROR, {
                        "step_number": i + 1,
                        "error": result.error
                    })

                # Stop on failure
                tts.speak(f"第{i+1}步失败，计划中止")
                console.print(f"\n[red]❌ Plan stopped at step {i+1} due to failure[/red]")
                return True

    # All steps succeeded
    if not dry_run:
        console.print(Panel(
            f"[bold green]✓ All {len(plan.plan)} steps completed successfully[/bold green]",
            border_style="green"
        ))

        complete_msg = f"所有{len(plan.plan)}个步骤已完成"
        if use_ui:
            event_bus.publish(EventType.TTS_START, {"text": complete_msg})
        tts.speak(complete_msg)

        # Publish execution complete event
        if use_ui:
            event_bus.publish(EventType.EXECUTION_COMPLETE, {
                "total_steps": len(plan.plan)
            })
    else:
        console.print(f"\n[yellow]Dry run: would execute {len(plan.plan)} steps[/yellow]")

    return True


@app.command()
def run(
    text: Optional[str] = typer.Option(None, "--text", "-t", help="直接输入文本，跳过 ASR"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将执行的操作，不实际执行"),
    plan_debug: bool = typer.Option(False, "--plan-debug", help="只显示计划（Plan），不执行"),
    no_llm: bool = typer.Option(False, "--no-llm", help="不使用 LLM，仅使用规则"),
    loop: bool = typer.Option(False, "--loop", "-l", help="循环模式，持续监听"),
    asr_engine: str = typer.Option("text", "--asr", help="ASR 引擎：text, google, whisper"),
    whisper_model: str = typer.Option("base", "--whisper-model", help="Whisper 模型：tiny, base, small, medium"),
    no_asr_correction: bool = typer.Option(False, "--no-asr-correction", help="禁用 LLM ASR 纠错"),
    ui: bool = typer.Option(False, "--ui", help="启动 Web UI 可视化界面")
):
    """
    Start the voice assistant (支持多步骤任务 + 增强语音识别).

    Examples:
        # Single-step
        python app/main.py run --text "把音量调到30%"

        # Multi-step
        python app/main.py run --text "打开Safari然后搜索Python教程"

        # Plan debug (show plan without executing)
        python app/main.py run --text "搜索天气，然后把音量调到50%" --plan-debug

        # Whisper ASR (高准确率，离线)
        python app/main.py run --asr whisper --whisper-model base --loop

        # Google ASR (在线，优化参数 + LLM 纠错)
        python app/main.py run --asr google --loop

        # 禁用 LLM 纠错
        python app/main.py run --asr whisper --no-asr-correction --loop
    """
    # Validate configuration
    if not dry_run and not no_llm and not config.validate():
        console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY not set in .env file")
        console.print("Please copy .env.example to .env and set your API key")
        raise typer.Exit(1)

    # Start Web UI if requested
    webui_server = None
    if ui:
        try:
            webui_server = create_webui_server(port=5001)
            webui_server.start(open_browser=True)
            console.print("[green]✓ Web UI started at http://127.0.0.1:5001[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Failed to start Web UI: {e}[/yellow]")

    # Welcome message
    mode_str = "PLAN DEBUG" if plan_debug else ("DRY RUN" if dry_run else "EXECUTE")
    asr_correction_str = "Enabled" if not no_asr_correction and not no_llm else "Disabled"
    console.print(Panel(
        "[bold]Voice-activated macOS Assistant[/bold]\n"
        "[dim]支持多步骤任务组合 + 高准确率语音识别[/dim]\n\n"
        f"Mode: {mode_str}\n"
        f"LLM: {'Disabled' if no_llm else 'Enabled'}\n"
        f"Model: {config.CLAUDE_MODEL if not no_llm else 'N/A'}\n"
        f"ASR Engine: {asr_engine}\n"
        f"ASR Correction: {asr_correction_str}" +
        (f"\nWhisper Model: {whisper_model}" if asr_engine == "whisper" else "") +
        (f"\n[bold green]Web UI: http://127.0.0.1:5001[/bold green]" if ui else ""),
        title="🎙️ Welcome",
        border_style="blue"
    ))

    # Publish system ready event
    if ui:
        event_bus = get_event_bus()
        event_bus.publish(EventType.SYSTEM_READY, {
            "mode": mode_str,
            "llm_enabled": not no_llm,
            "asr_engine": asr_engine
        })

    # Initialize components
    console.print("[cyan]Initializing components...[/cyan]")
    planner = create_planner(use_llm=not no_llm)
    executor = create_executor(dry_run=dry_run)
    verbalizer = create_verbalizer()
    tts = create_tts_engine()

    # Single text mode
    if text:
        if ui:
            event_bus = get_event_bus()
            event_bus.publish(EventType.ASR_COMPLETE, {"text": text})

        console.print(f"\n[bold]User:[/bold] {text}")
        process_utterance(text, planner, executor, verbalizer, tts, dry_run, plan_debug, ui)
        return

    # Loop mode - create ASR engine with new options
    from app.asr import create_asr_engine

    enable_llm_correction = not no_asr_correction and not no_llm
    asr = create_asr_engine(
        engine=asr_engine,
        whisper_model=whisper_model,
        enable_llm_correction=enable_llm_correction
    )

    if asr_engine == "text":
        console.print("\n[green]✓ Ready! Type your commands (type 'exit' to quit)[/green]\n")
    else:
        console.print(f"\n[green]✓ Ready! Start speaking with {asr_engine.upper()} ASR (say '退出' to quit)[/green]\n")

    while True:
        # Wait for user to click "Continue" if using UI
        if ui:
            event_bus = get_event_bus()
            event_bus.publish(EventType.READY_FOR_NEXT, {
                "message": "准备开始下一条指令"
            })

            # Wait for user to click continue button
            should_continue_recording = event_bus.wait_for_continue(timeout=600.0)
            if not should_continue_recording:
                console.print("\n[yellow]⏱️ Timeout or user stopped[/yellow]")
                break

        # Publish ASR start event
        if ui:
            event_bus.publish(EventType.ASR_START, {})

        # Get user input
        user_text = asr.transcribe_once()

        if not user_text:
            break

        # Publish ASR complete event
        if ui:
            event_bus.publish(EventType.ASR_COMPLETE, {"text": user_text})

        console.print(f"\n[bold]User:[/bold] {user_text}")

        # Process
        should_continue = process_utterance(
            user_text, planner, executor, verbalizer, tts, dry_run, plan_debug, ui
        )

        if not should_continue:
            break

        # Exit if not in loop mode
        if not loop and text is None:
            # In interactive mode without --loop, continue
            pass

    console.print("\n[blue]Goodbye! 👋[/blue]")


@app.command()
def test():
    """Run basic functionality tests."""
    console.print("[cyan]Running basic tests...[/cyan]\n")

    # Test configuration
    console.print("[bold]1. Testing configuration...[/bold]")
    console.print(f"   API Key set: {bool(config.ANTHROPIC_API_KEY)}")
    console.print(f"   Model: {config.CLAUDE_MODEL}")
    console.print(f"   Prompts dir: {config.PROMPTS_DIR.exists()}")

    # Test planner (rule-based only)
    console.print("\n[bold]2. Testing rule-based planner...[/bold]")
    planner = create_planner(use_llm=False)
    test_cases = [
        "把音量调到50%",
        "搜索Python教程",
        "记录明天开会"
    ]

    for test_text in test_cases:
        intent = planner.plan(test_text)
        console.print(f"   '{test_text}' → {intent.intent}")

    # Test TTS
    console.print("\n[bold]3. Testing TTS...[/bold]")
    tts = create_tts_engine()
    console.print("   Speaking test message...")
    tts.speak("测试成功")

    console.print("\n[green]✓ Basic tests completed[/green]")


if __name__ == "__main__":
    app()
