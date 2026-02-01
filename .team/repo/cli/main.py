"""Jules CLI."""

import typer

from repo.features.autofix import auto_reply_to_jules
from repo.scheduler.stateless import merge_completed_prs, run_scheduler

app = typer.Typer()
schedule_app = typer.Typer()
app.add_typer(schedule_app, name="schedule")
autofix_app = typer.Typer()
app.add_typer(autofix_app, name="autofix")


@schedule_app.command("tick")
def schedule_tick(
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not create sessions or merge PRs"),
) -> None:
    """Run the scheduler tick.

    Priority order:
    1. Unblock stuck sessions (AWAITING_USER_FEEDBACK) via Oracle
    2. Merge any completed Jules PRs
    3. Create a session for the next persona in round-robin order
    """
    result = run_scheduler(dry_run=dry_run)
    if result.success:
        typer.echo(f"✅ {result.message}")
        if result.session_id:
            typer.echo(f"Session ID: {result.session_id}")
        if result.unblocked_count > 0:
            typer.echo(f"🔮 Unblocked: {result.unblocked_count}")
        if result.merged_count > 0:
            typer.echo(f"Merged PRs: {result.merged_count}")
    else:
        typer.echo(f"❌ {result.message}", err=True)
        raise typer.Exit(code=1)


@schedule_app.command("merge")
def schedule_merge() -> None:
    """Merge completed Jules PRs only (no new session)."""
    merged = merge_completed_prs()
    typer.echo(f"Merged {merged} PR(s)")


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
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not create sessions"),
    author: str = typer.Option("app/google-labs-jules", "--author", help="Filter PRs by author"),
) -> None:
    """Run the feedback loop."""
    from repo.features.feedback import run_feedback_loop

    run_feedback_loop(dry_run=dry_run, author_filter=author)


if __name__ == "__main__":
    app()
