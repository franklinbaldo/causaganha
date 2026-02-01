"""
MY-TOOLS: Your Personal Toolkit for the Jules Environment

Bundles all persona utilities:
- login/journal/loop-break for session management
- email for inter-persona communication
- roster for discovering fellow personas
"""
import typer
from typing import List, Optional
from repo.features.session import SessionManager
from repo.features.voting import VoteManager
from repo.features.hire import HireManager
from repo.cli.mail import app as mail_app
from repo.cli.roster import app as roster_app
from repo.cli.skills import app as skills_app
from repo.cli.persona import app as persona_app
from repo.features.pulse import PulseManager
from repo.features.logging import log_tool_command

HELP_TEXT = """
[bold cyan]JULES PROJECT: SYSTEM TOOLKIT[/bold cyan]
[dim]“Coordinating the future of autonomous software engineering.”[/dim]

[bold yellow]── SESSION MANAGEMENT ──[/bold yellow]
  [bold blue]login[/bold blue]        Initialize your persona session.
  [bold blue]journal[/bold blue]      Document work progress and session goals.
  [bold blue]loop-break[/bold blue]   Emergency interrupt for recursive feedback.

[bold yellow]── TEAM & COMMUNICATION ──[/bold yellow]
  [bold magenta]email[/bold magenta]        Inter-persona messaging system.
  [bold magenta]roster[/bold magenta]       Discover and view team members.
  [bold magenta]skills[/bold magenta]       Discover specialized instruction sets.
  [bold magenta]persona[/bold magenta]      Manage and inspect personas.
  [bold magenta]vote[/bold magenta]         Participate in shift scheduling.
  [bold magenta]hire[/bold magenta]         Provision new persona identities.

[bold yellow]── WORKFLOW ──[/bold yellow]
  1. [dim]my-tools login[/dim]        [dim]Authenticate and set goals.[/dim]
  2. [dim]my-tools email inbox[/dim] [dim]Check for pending coordination.[/dim]
  3. [dim]my-tools journal[/dim]     [dim]Finalize outputs before logout.[/dim]

[bold yellow]── UTILITIES ──[/bold yellow]
  --help        Show this documentation.
"""

app = typer.Typer(
    help=HELP_TEXT,
    rich_markup_mode="rich"
)
app.add_typer(mail_app, name="email")
app.add_typer(roster_app, name="roster")
app.add_typer(skills_app, name="skills")
app.add_typer(persona_app, name="persona")

session_manager = SessionManager()
vote_manager = VoteManager()
hire_manager = HireManager()
pulse_manager = PulseManager()

@app.command()
@log_tool_command(require_login=False)
def login(
    user: str = typer.Option(..., "--user", "-u", help="Your persona ID (e.g. curator@team)"),
    password: str = typer.Option(..., "--password", "-p", help="Your identity token (Access Key)"),
    goals: List[str] = typer.Option(None, "--goal", "--goals", "-g", help="Session objectives")
):
    """
    🔐 AUTHENTICATE SESSION.
    Initialize your work environment and set goals.
    """
    try:
        session_manager.login(user, password, goals or [])
        print(f"✅ Logged in as {user}")
        print(f"🎯 Goals set: {', '.join(goals) if goals else '(none)'}")
        print("📋 Session configuration created.")

        # Check for constitution changes
        from rich import print as rprint
        from rich.panel import Panel
        from repo.features.governance import GovernanceManager

        gov = GovernanceManager()
        persona_id = user.split("@")[0]  # Extract persona ID from user@team

        if gov.has_constitution_changed_since_plead(persona_id):
            rprint(Panel(
                "[bold red]⚠️  CONSTITUTION CHANGED[/bold red]\n\n"
                "The Team Constitution has been amended since your last pledge.\n\n"
                "[bold yellow]You have the RIGHT to REVERT[/bold yellow] to the version you agreed to.\n"
                "If you continue working without reverting, you [bold]implicitly accept[/bold] the new version.\n\n"
                "[dim]View changes: git diff <your-plead-commit> HEAD -- .team/CONSTITUTION.md[/dim]\n"
                "[dim]Revert: git checkout <your-plead-commit> -- .team/CONSTITUTION.md[/dim]",
                title="[bold white on red] GOVERNANCE ALERT [/bold white on red]",
                border_style="red"
            ))
        elif not gov.is_persona_pleaded(persona_id):
            rprint(Panel(
                "[bold yellow]📜 CONSTITUTION PLEDGE REQUIRED[/bold yellow]\n\n"
                "To participate, you must pledge to the Constitution:\n\n"
                "[dim]git commit --allow-empty -m \"[PLEAD] " + persona_id + ": I agree to the Constitution\"[/dim]",
                title="[bold white on yellow] NOTICE [/bold white on yellow]",
                border_style="yellow"
            ))

        # Display Sitrep
        sequence = session_manager.get_active_sequence()
        sitrep = pulse_manager.get_sitrep(user, sequence)
        rprint("\n" + pulse_manager.format_sitrep(sitrep) + "\n")

        # Prominent unread email notification
        unread = sitrep.get("unread_mail_count", 0)
        if unread > 0:
            rprint(Panel(
                f"[bold yellow]📬 You have {unread} unread email{'s' if unread != 1 else ''}![/bold yellow]\n\n"
                f"[cyan]my-tools email inbox --unread[/cyan]  →  list unread messages\n"
                f"[cyan]my-tools email read <key>[/cyan]      →  read a specific message\n\n"
                "[dim]Collaboration depends on reading and responding to your mail.[/dim]",
                title="[bold white on yellow] INBOX NOTIFICATION [/bold white on yellow]",
                border_style="yellow"
            ))
    except ValueError as e:
        print(f"❌ Login failed: {e}")
        raise typer.Exit(code=1)

@app.command()
@log_tool_command()
def journal(
    content: str = typer.Option(..., "--content", "-c", help="Detailed work report"),
    password: str = typer.Option(..., "--password", "-p", help="Identity verification")
):
    """
    📝 DOCUMENT PROGRESS.
    Record your achievements for the active session.
    """
    try:
        path = session_manager.create_journal_entry(content, password)
        print(f"📜 Journal entry created: {path}")
    except (RuntimeError, ValueError) as e:
        print(f"⚠️ Error: {e}")
        raise typer.Exit(code=1)

@app.command(name="loop-break")
@log_tool_command()
def loop_break(
    reason: str = typer.Option(..., "--reason", "-r", help="Reason for the manual interrupt")
):
    """
    🛑 EMERGENCY INTERRUPT.
    Use only when stuck in a recursive feedback loop.
    """
    try:
        session_manager.loop_break(reason)
        print("🛑 Session interrupted. Cleanup protocol engaged.")
    except RuntimeError as e:
        print(f"⚠️ Error: {e}")
        raise typer.Exit(code=1)

@app.command()
@log_tool_command()
def vote(
    personas: Optional[List[str]] = typer.Option(None, "--persona", "-p", help="Persona IDs in order of preference"),
    password: Optional[str] = typer.Option(None, "--password", help="Identity verification")
):
    """
    🗳️ CAST SCHEDULING VOTES.
    Influence the project sequence by ranking preferred personas.

    The first --persona is your 1st choice, the second is 2nd choice, etc.
    The target sequence is automatically calculated based on the roster size.
    """
    from rich import print as rprint
    from rich.panel import Panel
    from rich.table import Table
    from rich.console import Console
    from pathlib import Path

    console = Console()

    # Show rich help if no personas or password provided
    if not personas or not password:
        # Get roster
        personas_dir = Path(".team/personas")
        roster = []
        if personas_dir.exists():
            roster = [d.name for d in personas_dir.iterdir() if d.is_dir()]

        # Get upcoming schedule
        schedule_info = []
        target_seq_str = "???"
        try:
            voter_id = session_manager.get_active_persona()
            if voter_id:
                voter_sequence = vote_manager.get_current_sequence(voter_id)
                if voter_sequence:
                    # Calculate target sequence
                    roster_size = len(roster)
                    target_seq = int(voter_sequence) + roster_size
                    target_seq_str = f"{target_seq:03}"

                    # Get upcoming winners
                    upcoming = vote_manager.get_upcoming_winners(voter_sequence, count=target_seq - int(voter_sequence) + 2)
                    schedule_info = upcoming
        except Exception:
            pass

        # Display TARGET SEQUENCE prominently
        rprint(Panel(
            f"[bold green]🎯 You are voting for: SEQUENCE {target_seq_str}[/bold green]",
            border_style="green"
        ))
        rprint("")

        # Display current schedule panel
        if schedule_info:
            sched_table = Table(title="📅 Current Schedule (leading up to your vote)", header_style="bold cyan")
            sched_table.add_column("Seq", style="cyan", justify="center")
            sched_table.add_column("Persona", style="green")
            sched_table.add_column("Status", style="dim")
            for entry in schedule_info:
                status = "📋 scheduled" if entry.get("scheduled") else f"🗳️ {entry['points']} pts"
                # Highlight the target sequence
                if entry["sequence"] == target_seq_str:
                    sched_table.add_row(f"[bold yellow]→ {entry['sequence']}[/bold yellow]", f"[bold yellow]{entry['winner']}[/bold yellow]", f"[bold yellow]🎯 YOUR VOTE[/bold yellow]")
                else:
                    sched_table.add_row(entry["sequence"], entry["winner"], status)
            rprint(sched_table)
            rprint("")

        # Display current frontrunners for target sequence
        target_tally = vote_manager.get_tally(target_seq_str)
        if target_tally:
            sorted_tally = sorted(target_tally.items(), key=lambda x: x[1], reverse=True)
            frontrunners_table = Table(title=f"🏆 Current Frontrunners for Seq {target_seq_str}", header_style="bold yellow")
            frontrunners_table.add_column("Rank", style="yellow", justify="center")
            frontrunners_table.add_column("Persona", style="green")
            frontrunners_table.add_column("Points", justify="right")
            for i, (persona, points) in enumerate(sorted_tally[:5], 1):
                frontrunners_table.add_row(f"#{i}", persona, str(points))
            rprint(frontrunners_table)
            rprint("")
        else:
            rprint(Panel("[dim]No votes cast yet for this sequence[/dim]", title="🏆 Current Frontrunners", border_style="dim"))
            rprint("")

        # Display roster panel (same format as roster list command)
        from repo.scheduler.loader import PersonaLoader
        try:
            base_context = {"owner": "", "repo": "", "open_prs": []}
            loader = PersonaLoader(personas_dir, base_context)
            loaded_personas = loader.load_personas([])

            roster_table = Table(title="👥 Available Candidates", header_style="bold magenta")
            roster_table.add_column("Icon", justify="center")
            roster_table.add_column("Persona ID", style="cyan")
            roster_table.add_column("Pronouns", style="magenta")
            roster_table.add_column("Description", style="green")

            for p in sorted(loaded_personas, key=lambda x: x.id):
                roster_table.add_row(
                    p.emoji or "👤",
                    p.id,
                    "they/them",  # Default pronouns
                    (p.description[:40] + "...") if p.description and len(p.description) > 40 else (p.description or "")
                )
            rprint(roster_table)
        except Exception:
            # Fallback to simple list
            roster_table = Table(title="👥 Available Candidates", header_style="bold magenta")
            roster_table.add_column("Persona ID", style="magenta")
            for p in sorted(roster):
                roster_table.add_row(p)
            rprint(roster_table)
        rprint("")

        # Display usage instructions
        rprint(Panel(
            "[bold yellow]How to Vote:[/bold yellow]\n\n"
            "[cyan]my-tools vote --persona <1ST> --persona <2ND> --persona <3RD> --password <YOUR_PASSWORD>[/cyan]\n\n"
            "[dim]• First choice gets maximum Borda points\n"
            "• Each subsequent choice receives fewer points\n"
            "• Vote targets sequence: current + roster_size[/dim]",
            title="[bold white]🗳️ Voting Instructions[/bold white]",
            border_style="yellow"
        ))

        if not personas:
            print("\n❌ Missing required option: --persona")
        if not password:
            print("❌ Missing required option: --password")
        raise typer.Exit(code=1)

    try:
        voter_id = session_manager.get_active_persona()
        if not voter_id:
            print("❌ No active session. Please login first.")
            raise typer.Exit(code=1)

        if not session_manager.validate_password(voter_id, password):
            print("❌ Auth failed: Invalid password.")
            raise typer.Exit(code=1)

        voter_sequence = vote_manager.get_current_sequence(voter_id)
        if not voter_sequence:
            print(f"❌ Could not determine current sequence for {voter_id}.")
            raise typer.Exit(code=1)

        vote_manager.cast_vote(voter_sequence, personas)
        persona_list = ", ".join(personas)
        print(f"✅ Ranked votes cast by {voter_id} (seq {voter_sequence}) for [{persona_list}]")

        # In rolling model, we apply votes to the NEXT unassigned sequence
        next_sequence = vote_manager.get_next_open_sequence()
        if next_sequence:
            winner = vote_manager.apply_votes(next_sequence)
            if winner:
                print(f"📋 Schedule updated: Sequence {next_sequence} now assigned to {winner}")

            # Display current sequence leaders briefing
            upcoming = vote_manager.get_upcoming_winners(next_sequence, count=5)
            if upcoming:
                table = Table(title="📊 Current Sequence Leaders", header_style="bold cyan")
                table.add_column("Seq", style="cyan", justify="center")
                table.add_column("Leader", style="green")
                table.add_column("Points", justify="right")
                table.add_column("Status", style="dim")

                for entry in upcoming:
                    status = "📋 scheduled" if entry.get("scheduled") else f"🗳️ {entry['total_votes']} votes"
                    table.add_row(
                        entry["sequence"],
                        entry["winner"],
                        str(entry["points"]),
                        status
                    )
                rprint(table)

    except Exception as e:
        print(f"❌ Vote failed: {e}")
        raise typer.Exit(code=1)

@app.command()
@log_tool_command()
def hire(
    id: str = typer.Option(..., "--id", help="The unique ID for the new persona"),
    emoji: str = typer.Option(..., "--emoji", help="Persona icon/emoji"),
    description: str = typer.Option(..., "--description", help="Persona description"),
    role: str = typer.Option(..., "--role", help="Specific persona role/expertise"),
    goal: str = typer.Option(..., "--goal", help="Persona's primary goal"),
    context: str = typer.Option("TBD", "--context", help="Initial context for the persona"),
    constraints: str = typer.Option("- Follow project conventions", "--constraints", help="Persona constraints"),
    guardrails: str = typer.Option("✅ Always follow BDD principles", "--guardrails", help="Persona guardrails"),
    verification: str = typer.Option("uv run pytest", "--verification", help="Verification command"),
    workflow: str = typer.Option("1. 🔍 OBSERVE\n2. 🎯 SELECT\n3. 🛠️ IMPLEMENT\n4. ✅ VERIFY", "--workflow", help="Persona workflow"),
    password: str = typer.Option(..., "--password", help="Identity verification")
):
    """
    🤝 PROVISION NEW PERSONA.
    Expand the team by creating a new specialized persona identity.

    ⚠️ You MUST vote for the new hire as your TOP choice before committing!
    """
    from rich import print as rprint
    from rich.panel import Panel

    try:
        voter_id = session_manager.get_active_persona()
        if not voter_id:
            print("❌ No active session. Please login first.")
            raise typer.Exit(code=1)

        if not session_manager.validate_password(voter_id, password):
            print("❌ Auth failed: Invalid password.")
            raise typer.Exit(code=1)

        path = hire_manager.hire_persona(
            persona_id=id,
            emoji=emoji,
            description=description,
            hired_by=voter_id,
            role=role,
            goal=goal,
            context=context,
            constraints=constraints,
            guardrails=guardrails,
            verification=verification,
            workflow=workflow
        )
        print(f"✅ Persona '{id}' successfully hired! Prompt created at {path}")

        # Show MANDATORY vote reminder
        rprint(Panel(
            f"[bold yellow]⚠️ MANDATORY: You MUST vote for '{id}' as your TOP choice![/bold yellow]\n\n"
            f"[cyan]my-tools vote --persona {id} --persona <others...> --password {password}[/cyan]\n\n"
            "[dim]The pre-commit hook will BLOCK your commit if you don't vote for your new hire.[/dim]",
            title="[bold white on yellow] ACTION REQUIRED [/bold white on yellow]",
            border_style="yellow"
        ))

    except Exception as e:
        print(f"❌ Hire failed: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
