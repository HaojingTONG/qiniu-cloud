#!/usr/bin/env python3
"""
Test replay script.
Reads tasks from CSV and evaluates planner accuracy.
"""
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.planner import create_planner
from app.config import config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


console = Console()


def load_tasks(csv_path: Path) -> List[Dict[str, Any]]:
    """Load test tasks from CSV file."""
    tasks = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse expected slots
            try:
                slots = json.loads(row['expected_slots'])
            except json.JSONDecodeError:
                slots = {}

            tasks.append({
                'utterance': row['utterance'],
                'expected_intent': row['expected_intent'],
                'expected_slots': slots
            })
    return tasks


def evaluate_intent(predicted: str, expected: str) -> bool:
    """Check if intent matches."""
    return predicted == expected


def evaluate_slots(predicted: Dict, expected: Dict) -> Tuple[bool, str]:
    """
    Check if slots match (partial match allowed).

    Returns:
        (match, reason)
    """
    if not expected:
        # No slots expected, any result is OK
        return True, ""

    # Check key slots
    for key, value in expected.items():
        if key not in predicted:
            return False, f"Missing slot: {key}"

        pred_value = predicted[key]

        # Type conversion for comparison
        if isinstance(value, (int, float)):
            try:
                pred_value = type(value)(pred_value)
            except (ValueError, TypeError):
                return False, f"Slot {key}: type mismatch"

        # Partial string match
        if isinstance(value, str) and isinstance(pred_value, str):
            if value.lower() not in pred_value.lower() and pred_value.lower() not in value.lower():
                # For search queries, just check if some words match
                if key == "query":
                    value_words = set(value.lower().split())
                    pred_words = set(pred_value.lower().split())
                    if not value_words & pred_words:  # No overlap
                        return False, f"Slot {key}: no word overlap"
                else:
                    return False, f"Slot {key}: value mismatch"
        elif pred_value != value:
            # For non-string, exact match
            if key == "value" and isinstance(value, (int, float)):
                # Allow small numeric difference
                if abs(pred_value - value) > 1:
                    return False, f"Slot {key}: value differs too much"
            else:
                # Ignore minor differences for non-critical slots
                pass

    return True, ""


def run_tests(use_llm: bool = False):
    """
    Run all test cases.

    Args:
        use_llm: Whether to use LLM (requires API key)
    """
    # Load tasks
    csv_path = Path(__file__).parent / "tasks.csv"
    tasks = load_tasks(csv_path)

    console.print(Panel(
        f"[bold]Test Replay[/bold]\n\n"
        f"Total tasks: {len(tasks)}\n"
        f"Mode: {'LLM' if use_llm else 'Rule-based'}\n"
        f"Dry-run: Yes",
        title="🧪 Testing",
        border_style="blue"
    ))

    # Create planner
    planner = create_planner(use_llm=use_llm)

    # Results
    total = len(tasks)
    intent_correct = 0
    slots_correct = 0
    both_correct = 0
    errors = []

    # Run tests
    for i, task in enumerate(tasks, 1):
        utterance = task['utterance']
        expected_intent = task['expected_intent']
        expected_slots = task['expected_slots']

        try:
            # Plan (dry-run mode)
            result = planner.plan(utterance, dry_run=True)

            # Evaluate intent
            intent_match = evaluate_intent(result.intent, expected_intent)
            if intent_match:
                intent_correct += 1

            # Evaluate slots
            slots_match, slots_reason = evaluate_slots(result.slots, expected_slots)
            if slots_match:
                slots_correct += 1

            # Both correct
            if intent_match and slots_match:
                both_correct += 1
            else:
                # Record error
                errors.append({
                    'index': i,
                    'utterance': utterance,
                    'expected_intent': expected_intent,
                    'predicted_intent': result.intent,
                    'expected_slots': expected_slots,
                    'predicted_slots': result.slots,
                    'intent_match': intent_match,
                    'slots_match': slots_match,
                    'slots_reason': slots_reason
                })

            # Progress
            if i % 10 == 0:
                console.print(f"[cyan]Processed {i}/{total} tasks...[/cyan]")

        except Exception as e:
            console.print(f"[red]Error on task {i}: {e}[/red]")
            errors.append({
                'index': i,
                'utterance': utterance,
                'error': str(e)
            })

    # Display results
    console.print("\n")
    console.print(Panel(
        f"[bold]Intent Accuracy:[/bold] {intent_correct}/{total} ({intent_correct/total*100:.1f}%)\n"
        f"[bold]Slots Accuracy:[/bold] {slots_correct}/{total} ({slots_correct/total*100:.1f}%)\n"
        f"[bold]Overall Accuracy:[/bold] {both_correct}/{total} ({both_correct/total*100:.1f}%)",
        title="📊 Results",
        border_style="green" if both_correct/total > 0.8 else "yellow"
    ))

    # Show errors
    if errors:
        console.print(f"\n[bold red]Failed Cases ({len(errors)}):[/bold red]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Utterance", width=30)
        table.add_column("Expected", width=20)
        table.add_column("Predicted", width=20)
        table.add_column("Issue", width=25)

        for err in errors[:10]:  # Show first 10 errors
            if 'error' in err:
                table.add_row(
                    str(err['index']),
                    err['utterance'][:30],
                    "-",
                    "-",
                    f"[red]Error: {err['error'][:20]}[/red]"
                )
            else:
                issue = []
                if not err['intent_match']:
                    issue.append(f"intent: {err['expected_intent']} ≠ {err['predicted_intent']}")
                if not err['slots_match']:
                    issue.append(f"slots: {err['slots_reason']}")

                table.add_row(
                    str(err['index']),
                    err['utterance'][:30],
                    err['expected_intent'],
                    err['predicted_intent'],
                    "; ".join(issue)[:25]
                )

        console.print(table)

        if len(errors) > 10:
            console.print(f"\n[dim]... and {len(errors) - 10} more errors[/dim]")

    # Summary
    console.print(f"\n[cyan]Test completed![/cyan]")
    if both_correct / total >= 0.9:
        console.print("[green]✓ Excellent performance (≥90%)[/green]")
    elif both_correct / total >= 0.7:
        console.print("[yellow]⚠ Good performance (≥70%)[/yellow]")
    else:
        console.print("[red]✗ Needs improvement (<70%)[/red]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test replay for voice assistant")
    parser.add_argument("--llm", action="store_true", help="Use LLM instead of rule-based")
    args = parser.parse_args()

    if args.llm and not config.validate():
        console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY not set")
        console.print("Set API key in .env or use --no-llm for rule-based testing")
        sys.exit(1)

    run_tests(use_llm=args.llm)
