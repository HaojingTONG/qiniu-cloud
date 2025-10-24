#!/usr/bin/env python3
"""
测试多步骤任务规划（Plan）功能。
Test multi-step task planning (Plan) functionality.

Usage:
    python tests/plan_replay.py
"""
import sys
import csv
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.planner import create_planner
from app.schema import Intent, Plan
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


def load_test_cases(csv_path: Path):
    """Load test cases from CSV file."""
    test_cases = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append({
                "utterance": row["utterance"],
                "expected_type": row["expected_type"],
                "expected_steps": int(row["expected_steps"]),
                "description": row["description"]
            })

    return test_cases


def test_multi_step_planning():
    """Test multi-step planning functionality."""
    console.print("\n[bold cyan]Multi-Step Task Planning Test Suite[/bold cyan]\n")

    # Load test cases
    csv_path = Path(__file__).parent / "plan_tasks.csv"
    test_cases = load_test_cases(csv_path)

    console.print(f"Loaded {len(test_cases)} test cases\n")

    # Create planner (with LLM)
    console.print("[cyan]Initializing planner with LLM...[/cyan]")
    planner = create_planner(use_llm=True)

    # Test results
    results = []

    for i, test in enumerate(test_cases, 1):
        console.print(f"\n[bold]Test {i}/{len(test_cases)}:[/bold] {test['utterance']}")
        console.print(f"[dim]Expected: {test['expected_type']} with {test['expected_steps']} step(s)[/dim]")

        try:
            # Parse
            result = planner.parse_plan_or_intent(test["utterance"], dry_run=False)

            # Check type
            actual_type = "plan" if isinstance(result, Plan) else "intent"
            type_match = actual_type == test["expected_type"]

            # Check steps
            if isinstance(result, Plan):
                actual_steps = len(result.plan)
                steps_match = actual_steps == test["expected_steps"]

                console.print(f"[green]✓ Got Plan with {actual_steps} steps[/green]")
                console.print(f"  Summary: {result.summary}")

                for j, intent in enumerate(result.plan, 1):
                    console.print(f"  Step {j}: [{intent.intent}] {intent.slots}")
            else:
                actual_steps = 1
                steps_match = actual_steps == test["expected_steps"]

                console.print(f"[yellow]Got Intent: [{result.intent}] {result.slots}[/yellow]")

            # Overall result
            passed = type_match and steps_match

            results.append({
                "utterance": test["utterance"],
                "expected_type": test["expected_type"],
                "actual_type": actual_type,
                "expected_steps": test["expected_steps"],
                "actual_steps": actual_steps,
                "passed": passed
            })

            if passed:
                console.print("[bold green]✓ PASS[/bold green]")
            else:
                console.print(f"[bold red]✗ FAIL[/bold red] - Type match: {type_match}, Steps match: {steps_match}")

        except Exception as e:
            console.print(f"[bold red]✗ ERROR: {e}[/bold red]")
            results.append({
                "utterance": test["utterance"],
                "expected_type": test["expected_type"],
                "actual_type": "error",
                "expected_steps": test["expected_steps"],
                "actual_steps": 0,
                "passed": False
            })

    # Summary
    console.print("\n" + "=" * 80 + "\n")
    console.print("[bold cyan]Test Summary[/bold cyan]\n")

    # Create results table
    table = Table(title="Test Results")
    table.add_column("Utterance", style="cyan", no_wrap=False, max_width=40)
    table.add_column("Expected", style="yellow")
    table.add_column("Actual", style="blue")
    table.add_column("Steps", style="magenta")
    table.add_column("Result", style="green")

    passed_count = 0
    for result in results:
        if result["passed"]:
            passed_count += 1
            status = "✓ PASS"
            status_style = "green"
        else:
            status = "✗ FAIL"
            status_style = "red"

        table.add_row(
            result["utterance"],
            result["expected_type"],
            result["actual_type"],
            f"{result['actual_steps']}/{result['expected_steps']}",
            f"[{status_style}]{status}[/{status_style}]"
        )

    console.print(table)

    # Stats
    total = len(results)
    pass_rate = (passed_count / total * 100) if total > 0 else 0

    console.print(f"\n[bold]Overall Results:[/bold]")
    console.print(f"  Total: {total}")
    console.print(f"  Passed: [green]{passed_count}[/green]")
    console.print(f"  Failed: [red]{total - passed_count}[/red]")
    console.print(f"  Pass Rate: [{'green' if pass_rate >= 80 else 'yellow'}]{pass_rate:.1f}%[/]")

    if pass_rate >= 80:
        console.print("\n[bold green]✓ Test suite PASSED[/bold green]")
    else:
        console.print("\n[bold red]✗ Test suite FAILED[/bold red]")

    return pass_rate >= 80


if __name__ == "__main__":
    try:
        success = test_multi_step_planning()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Test suite error: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
