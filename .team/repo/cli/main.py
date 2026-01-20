"""Jules CLI."""

import typer

from repo.features.autofix import auto_reply_to_jules
from repo.scheduler.managers import BranchManager
from repo.scheduler.engine import run_scheduler

app = typer.Typer()
schedule_app = typer.Typer()
app.add_typer(schedule_app, name="schedule")
autofix_app = typer.Typer()
app.add_typer(autofix_app, name="autofix")
sync_app = typer.Typer()
app.add_typer(sync_app, name="sync")


@schedule_app.command("tick")
def schedule_tick(
    all: bool = typer.Option(False, "--all", help="Run all enabled prompts regardless of schedule"),  # noqa: FBT001, FBT003, A002
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not create sessions"),  # noqa: FBT001, FBT003
    prompt_id: str = typer.Option(None, "--prompt-id", help="Run only specific prompt ID or prompt path"),
    reset: bool = typer.Option(False, "--reset", help="Reset cycle and start from the first persona"),
) -> None:
    """Run the scheduler tick."""
    result = run_scheduler(dry_run=dry_run, persona_id=prompt_id, reset=reset)
    if result.success:
        typer.echo(f"✅ {result.message}")
        if result.session_id:
            typer.echo(f"Session ID: {result.session_id}")
    else:
        typer.echo(f"❌ {result.message}", err=True)
        if result.error:
            typer.echo(f"Error details: {result.error}", err=True)
        raise typer.Exit(code=1)


@autofix_app.command("analyze")
def autofix_analyze(
    pr_number: int = typer.Argument(..., help="PR number to analyze"),
) -> None:
    """Analyze a PR and auto-fix with Jules."""
    auto_reply_to_jules(pr_number)


feedback_app = typer.Typer()
app.add_typer(feedback_app, name="feedback")


@feedback_app.command("loop")
def feedback_loop(
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not create sessions"),  # noqa: FBT001, FBT003
    author: str = typer.Option("app/google-labs-jules", "--author", help="Filter PRs by author"),
) -> None:
    """Run the feedback loop."""
    from repo.features.feedback import run_feedback_loop

    run_feedback_loop(dry_run=dry_run, author_filter=author)


@sync_app.command("merge-main")
def sync_merge_main(
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not execute changes"),  # noqa: FBT001, FBT003
) -> None:
    """Directly merge jules → main (no PR)."""
    mgr = BranchManager()
    mgr.merge_jules_into_main_direct(dry_run=dry_run)


if __name__ == "__main__":
    app()
