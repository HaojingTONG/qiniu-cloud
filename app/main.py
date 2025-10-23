#!/usr/bin/env python3
"""
Voice-activated macOS assistant CLI.
Main entry point for the application.
"""
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.planner import create_planner
from app.executor import create_executor
from app.asr import create_asr_engine
from app.tts import create_tts_engine
from app.verbalizer import create_verbalizer
from app.utils import logger


app = typer.Typer(help="Voice-activated macOS assistant")
console = Console()


def process_utterance(
    text: str,
    planner,
    executor,
    verbalizer,
    tts,
    dry_run: bool = False
) -> bool:
    """
    Process a single user utterance.

    Args:
        text: User utterance
        planner: Planner instance
        executor: Executor instance
        verbalizer: Verbalizer instance
        tts: TTS engine instance
        dry_run: If True, only show what would be executed

    Returns:
        True to continue, False to exit
    """
    # Check for exit commands
    if text.lower() in ["exit", "quit", "退出", "拜拜", "再见"]:
        tts.speak("再见！")
        return False

    try:
        # Plan intent
        console.print(f"\n[cyan]📝 Planning...[/cyan]")
        intent = planner.plan(text, dry_run=dry_run)

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
                response = typer.confirm("继续执行？", default=False)
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

            # Speak result
            result_msg = verbalizer.generate_result_message(intent, result)
            tts.speak(result_msg)

        return True

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error processing utterance: {e}")
        console.print(f"[bold red]Error:[/bold red] {e}")
        tts.speak("抱歉，出错了")
        return True


@app.command()
def run(
    text: Optional[str] = typer.Option(None, "--text", "-t", help="直接输入文本，跳过 ASR"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将执行的操作，不实际执行"),
    no_llm: bool = typer.Option(False, "--no-llm", help="不使用 LLM，仅使用规则"),
    loop: bool = typer.Option(False, "--loop", "-l", help="循环模式，持续监听")
):
    """
    Start the voice assistant.

    Examples:
        python app/main.py --text "把音量调到30%"
        python app/main.py --text "搜索Python教程" --dry-run
        python app/main.py --loop
    """
    # Validate configuration
    if not dry_run and not no_llm and not config.validate():
        console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY not set in .env file")
        console.print("Please copy .env.example to .env and set your API key")
        raise typer.Exit(1)

    # Welcome message
    console.print(Panel(
        "[bold]Voice-activated macOS Assistant[/bold]\n\n"
        f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n"
        f"LLM: {'Disabled' if no_llm else 'Enabled'}\n"
        f"Model: {config.CLAUDE_MODEL if not no_llm else 'N/A'}",
        title="🎙️ Welcome",
        border_style="blue"
    ))

    # Initialize components
    console.print("[cyan]Initializing components...[/cyan]")
    planner = create_planner(use_llm=not no_llm)
    executor = create_executor(dry_run=dry_run)
    verbalizer = create_verbalizer()
    tts = create_tts_engine()

    # Single text mode
    if text:
        console.print(f"\n[bold]User:[/bold] {text}")
        process_utterance(text, planner, executor, verbalizer, tts, dry_run)
        return

    # Loop mode (with or without --loop flag)
    asr = create_asr_engine()
    console.print("\n[green]✓ Ready! Start speaking (type 'exit' to quit)[/green]\n")

    while True:
        # Get user input
        user_text = asr.transcribe_once()

        if not user_text:
            break

        console.print(f"\n[bold]User:[/bold] {user_text}")

        # Process
        should_continue = process_utterance(
            user_text, planner, executor, verbalizer, tts, dry_run
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
