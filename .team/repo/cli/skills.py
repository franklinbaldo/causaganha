import typer
from rich.console import Console
from rich.table import Table
from repo.features.skills import SkillsManager
from repo.features.logging import log_tool_command

app = typer.Typer(
    help="🛠️ Manage and discover specialized skills.",
    no_args_is_help=True,
    rich_markup_mode="rich"
)

console = Console()
manager = SkillsManager()

@app.command(name="list")
@log_tool_command(prefix="skills")
def list_skills():
    """
    📜 LIST AVAILABLE SKILLS.
    Discover specialized instruction sets and tools.
    """
    skills = manager.list_skills()
    
    if not skills:
        console.print("[yellow]No specialized skills discovered in .team/skills/[/yellow]")
        return

    table = Table(title="[bold cyan]JULES PROJECT: SPECIALIZED SKILLS[/bold cyan]", header_style="bold magenta")
    table.add_column("Skill ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Description", style="green")

    for skill in skills:
        table.add_row(skill["id"], skill["name"], skill["description"])

    console.print(table)
    console.print(f"\n[dim]Total skills: {len(skills)}[/dim]")
    console.print("[dim]Use 'view_file' recursively to read SKILL.md for details.[/dim]")

if __name__ == "__main__":
    app()
