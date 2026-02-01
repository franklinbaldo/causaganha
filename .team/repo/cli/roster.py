from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from repo.scheduler.loader import PersonaLoader
from repo.features.logging import log_tool_command

app = typer.Typer(
    name="roster",
    help="👥 Discover your fellow personas and access team records.",
    no_args_is_help=True,
    rich_markup_mode="rich"
)

console = Console()


def get_personas_dir() -> Path:
    """Find the personas directory."""
    candidates = [
        Path(".team/personas"),
        Path("personas"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not find personas records")


@app.command(name="list")
@log_tool_command(prefix="roster")
def list_personas():
    """
    👥 VIEW TEAM MEMBERS.
    List all active personas in the project environment.
    """
    try:
        personas_dir = get_personas_dir()
        table = Table(title="[bold white]TEAM PROJECT: ACTIVE TEAM ROSTER[/bold white]", header_style="bold cyan")
        table.add_column("Icon", justify="center")
        table.add_column("Persona ID", style="cyan")
        table.add_column("Pronouns", style="magenta")
        table.add_column("Description", style="green")

        # Provide a minimal base_context for roster listing (no template rendering needed)
        base_context = {"owner": "", "repo": "", "open_prs": []}
        loader = PersonaLoader(personas_dir, base_context)
        personas = loader.load_personas([])

        if not personas:
            console.print("[bold red]❌ Error:[/bold red] No personas found")
            raise typer.Exit(code=1)

        for p in personas:
            table.add_row(
                p.emoji or "👤",
                p.id,
                p.frontmatter.get("pronouns", "they/them") if hasattr(p, 'frontmatter') else "they/them",
                p.description or "No description available."
            )

        console.print(table)
        console.print(f"\n[dim]Total personas: {len(personas)}[/dim]")
        console.print("[dim]Use 'my-tools roster view <persona_id>' for full details.[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="view")
@log_tool_command(prefix="roster")
def view_persona(
    persona_id: str = typer.Argument(..., help="The Persona ID to inspect (e.g., refactor, curator)")
):
    """
    🔍 VIEW DETAILS.
    Retrieve full documentation for a specific persona.
    """
    try:
        personas_dir = get_personas_dir()
        base_context = {"owner": "", "repo": "", "open_prs": []}
        loader = PersonaLoader(personas_dir, base_context)
        
        # Find the persona file
        persona_path = personas_dir / persona_id / "prompt.md.j2"
        if not persona_path.exists():
            persona_path = personas_dir / persona_id / "prompt.md"
        
        if not persona_path.exists():
            console.print(f"[bold red]❌ Error:[/bold red] Persona '{persona_id}' not found.")
            raise typer.Exit(code=1)

        persona = loader.load_persona(persona_path)

        # Render Persona Details
        rprint = console.print
        
        rprint(Panel(
            f"[bold cyan]ID:[/bold cyan] {persona.id}\n"
            f"[bold cyan]Description:[/bold cyan] {persona.description or 'N/A'}\n"
            f"[bold cyan]Emoji:[/bold cyan] {persona.emoji or '👤'}",
            title=f"[bold white]PERSONA PROFILE: {persona_id.upper()}[/bold white]",
            border_style="cyan"
        ))

        if persona.prompt_body:
            rprint("\n[bold yellow]PROMPT TEMPLATE (RGCCOV Architecture):[/bold yellow]")
            rprint(Markdown(persona.prompt_body))
            
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
