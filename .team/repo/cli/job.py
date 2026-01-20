import typer
from typing import List, Optional
from repo.features.session import SessionManager

app = typer.Typer(
    help="""
    JOB SIMULATION INTERFACE: Authenticate and track your work execution.
    
    This tool simulates a professional work environment. 
    You must LOGIN at the start of your session to receive your goals.
    You must write a JOURNAL entry before finishing your task.
    If you are STUCK, use loop-break.
    """
)

session_manager = SessionManager()

@app.command()
def login(
    user: str = typer.Option(..., "--user", help="Your persona ID (e.g. weaver@team)"),
    password: str = typer.Option(..., "--password", help="Your unique identity token (UUIDv5)"),
    goals: List[str] = typer.Option([], "--goals", help="List of goals for this session")
):
    """
    Clock in for work. Configures your environment and sets goals.
    """
    try:
        session_manager.login(user, password, goals)
        print(f"✅ Logged in as {user}")
        print(f"🎯 Goals set: {', '.join(goals)}")
        print("Creating session configuration...")
    except ValueError as e:
        print(f"❌ Login failed: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise typer.Exit(code=1)

@app.command()
def journal(
    content: str = typer.Option(..., "--content", help="Description of how you executed your goals"),
    password: str = typer.Option(..., "--password", help="Identity verification")
):
    """
    File a journal entry. Document your work execution.
    """
    try:
        path = session_manager.create_journal_entry(content, password)
        print(f"✅ Journal entry saved to {path}")
    except ValueError as e:
        print(f"❌ Auth failed: {e}")
        raise typer.Exit(code=1)
    except RuntimeError as e:
        print(f"❌ Session error: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise typer.Exit(code=1)

@app.command(name="loop-break")
def loop_break(
    reason: str = typer.Option(..., "--reason", help="Why are you stopping?")
):
    """
    EMERGENCY STOP. Use this if you are stuck in a loop or cannot proceed.
    """
    try:
        session_manager.loop_break(reason)
        print("🛑 Session STOPPED. Context captured.")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
