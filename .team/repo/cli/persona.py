"""Persona management CLI commands."""

import typer
from pathlib import Path
from typing import Optional
from rich import print as rprint
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    help="""
    [bold cyan]PERSONA MANAGEMENT[/bold cyan]

    Tools for managing and inspecting personas in the Jules system.
    """,
    rich_markup_mode="rich"
)

console = Console()


@app.command()
def render(
    persona_id: str = typer.Argument(
        ...,
        help="Persona ID to render (e.g., 'curator', 'meta')"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Save rendered prompt to file"
    ),
    preview: bool = typer.Option(
        False, "--preview", "-p",
        help="Show first 1000 characters only"
    )
):
    """
    🎨 RENDER PERSONA PROMPT.

    Renders a persona's full prompt with all context variables injected.
    Useful for debugging templates and previewing what Jules sessions receive.
    """
    try:
        from repo.scheduler.loader import PersonaLoader

        # Initialize loader
        personas_dir = Path(".team/personas")
        if not personas_dir.exists():
            rprint("[red]❌ Error: .team/personas directory not found[/red]")
            raise typer.Exit(code=1)

        loader = PersonaLoader(personas_dir=personas_dir)

        # Load the persona
        personas = loader.load_personas([f'personas/{persona_id}/prompt.md.j2'])

        if not personas:
            rprint(f"[red]❌ Error: Persona '{persona_id}' not found[/red]")
            rprint(f"[dim]Looking for: .team/personas/{persona_id}/prompt.md.j2[/dim]")
            raise typer.Exit(code=1)

        persona = personas[0]

        # Output to file or console
        if output:
            output.write_text(persona.prompt_body)
            rprint(f"[green]✅ Rendered prompt saved to {output}[/green]")
        elif preview:
            rprint(Panel(
                persona.prompt_body[:1000] + "\n\n[dim]... (truncated)[/dim]",
                title=f"🎨 {persona.emoji} {persona.id}",
                subtitle=f"{len(persona.prompt_body)} characters total"
            ))
        else:
            # Show full prompt with syntax highlighting
            syntax = Syntax(persona.prompt_body, "markdown", theme="monokai", line_numbers=False)
            console.print(Panel(
                syntax,
                title=f"🎨 {persona.emoji} {persona.id}",
                subtitle=persona.description
            ))

    except ImportError as e:
        rprint(f"[red]❌ Error: Missing dependency: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]❌ Error rendering persona: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def validate(
    persona_id: Optional[str] = typer.Argument(
        None,
        help="Specific persona to validate (validates all if not specified)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show detailed validation results"
    )
):
    """
    ✅ VALIDATE PERSONA(S).

    Checks that persona templates are valid and can be rendered without errors.
    Validates required fields, template syntax, and context variables.
    """
    try:
        from repo.scheduler.loader import PersonaLoader
        import uuid

        personas_dir = Path(".team/personas")
        if not personas_dir.exists():
            rprint("[red]❌ Error: .team/personas directory not found[/red]")
            raise typer.Exit(code=1)

        loader = PersonaLoader(personas_dir=personas_dir)

        # Determine which personas to validate
        if persona_id:
            personas = loader.load_personas([f'personas/{persona_id}/prompt.md.j2'])
            if not personas:
                rprint(f"[red]❌ Error: Persona '{persona_id}' not found[/red]")
                raise typer.Exit(code=1)
        else:
            personas = loader.load_personas([])

        # Create results table
        table = Table(title="Persona Validation Results")
        table.add_column("Persona", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Issues", style="yellow")

        failed = []
        passed = []

        for persona in personas:
            issues = []

            # Check required fields
            if not persona.id:
                issues.append("Missing ID")
            if not persona.emoji:
                issues.append("Missing emoji")
            if not persona.description:
                issues.append("Missing description")
            if len(persona.prompt_body) < 100:
                issues.append("Prompt too short")

            # Check password injection
            expected_password = str(uuid.uuid5(uuid.NAMESPACE_DNS, persona.id))
            if expected_password not in persona.prompt_body:
                issues.append("Password not injected")

            # Check session protocol
            if "my-tools" not in persona.prompt_body.lower():
                issues.append("Missing session protocol")

            # Check RGCCOV sections
            if "Role" not in persona.prompt_body and "## 🎭 Role" not in persona.prompt_body:
                issues.append("Missing Role section")
            if "Goal" not in persona.prompt_body and "## 🎯 Goal" not in persona.prompt_body:
                issues.append("Missing Goal section")

            # Add to results
            if issues:
                failed.append(persona.id)
                status = "❌ FAILED"
                table.add_row(
                    f"{persona.emoji} {persona.id}",
                    status,
                    ", ".join(issues)
                )
            else:
                passed.append(persona.id)
                if verbose:
                    table.add_row(
                        f"{persona.emoji} {persona.id}",
                        "✅ PASSED",
                        "All checks passed"
                    )

        # Display results
        console.print(table)
        console.print()

        # Summary
        total = len(personas)
        rprint(f"[bold]Summary:[/bold] {len(passed)}/{total} personas passed validation")

        if failed:
            rprint(f"[red]Failed personas: {', '.join(failed)}[/red]")
            raise typer.Exit(code=1)
        else:
            rprint("[green]✅ All personas are valid![/green]")

    except ImportError as e:
        rprint(f"[red]❌ Error: Missing dependency: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]❌ Error during validation: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def list():
    """
    📋 LIST ALL PERSONAS.

    Shows all available personas with their ID, emoji, and description.
    """
    try:
        from repo.scheduler.loader import PersonaLoader

        personas_dir = Path(".team/personas")
        if not personas_dir.exists():
            rprint("[red]❌ Error: .team/personas directory not found[/red]")
            raise typer.Exit(code=1)

        loader = PersonaLoader(personas_dir=personas_dir)

        personas = loader.load_personas([])

        if not personas:
            rprint("[yellow]⚠️  No personas found[/yellow]")
            return

        # Create table
        table = Table(title=f"Available Personas ({len(personas)})")
        table.add_column("Emoji", style="cyan", width=5)
        table.add_column("ID", style="green")
        table.add_column("Description", style="white")

        for persona in sorted(personas, key=lambda p: p.id):
            table.add_row(
                persona.emoji,
                persona.id,
                persona.description[:80] + "..." if len(persona.description) > 80 else persona.description
            )

        console.print(table)

    except ImportError as e:
        rprint(f"[red]❌ Error: Missing dependency: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]❌ Error listing personas: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
