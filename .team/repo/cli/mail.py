import typer
from typing import List, Optional
import os
from repo.features.mail import (
    send_message,
    list_inbox,
    get_message,
    mark_read,
    _get_backend,
    MAIL_ROOT
)
from repo.features.mail_handler import run_sync
from repo.features.logging import log_tool_command

app = typer.Typer(
    help="""
    [bold cyan]SYSTEM MAIL INTERFACE (SMI)[/bold cyan]
    
    A secure communication protocol for JULES project personas.
    All transmissions are logged for project coordination.
    """,
    rich_markup_mode="rich"
)

@app.command()
@log_tool_command(prefix="email")
def send(
    to: str = typer.Option(
        ..., "--to", 
        help="Recipient Persona ID (e.g., curator@team)"
    ),
    subject: str = typer.Option(
        ..., "--subject", "-s", 
        help="Message subject"
    ),
    body: str = typer.Option(
        ..., "--body", "-b", 
        help="Message content"
    ),
    from_id: str = typer.Option(
        None, "--from", "-f", 
        help="Sender Persona ID (defaults to active session)",
        envvar="JULES_PERSONA"
    ),
    attach: Optional[List[str]] = typer.Option(
        None, "--attach", "-a", 
        help="File attachments"
    )
):
    """
    📬 SEND MESSAGE.
    Transmit a new message to another persona.
    """
    if not from_id:
        from_id = os.environ.get("JULES_PERSONA")
        if not from_id:
            from_id = _get_active_persona_from_session()

    if not from_id:
        print("❌ Error: Persona ID could not be determined. Please login.")
        raise typer.Exit(code=1)
        
    try:
        key = send_message(from_id, to, subject, body, attach)
        print(f"✅ Message sent successfully (Key: {key})")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        raise typer.Exit(code=1)

def _get_active_persona_from_session() -> Optional[str]:
    from repo.features.session import SessionManager
    sm = SessionManager()
    return sm.get_active_persona()

@app.command()
@log_tool_command(prefix="email")
def inbox(
    persona: str = typer.Option(
        None, "--persona", "-p",
        help="Persona ID to check (defaults to active session)"
    ),
    unread: bool = typer.Option(
        False, "--unread", "-u",
        help="Filter for unread messages"
    ),
    limit: int = typer.Option(
        None, "--limit", "-l",
        help="Limit number of messages to display"
    )
):
    """
    📥 VIEW INBOX.
    List messages in the specified persona's inbox.
    """
    if not persona:
        persona = os.environ.get("JULES_PERSONA")
        if not persona:
            persona = _get_active_persona_from_session()

    if not persona:
        print("❌ Error: Persona ID required. Please login.")
        raise typer.Exit(code=1)

    try:
        messages = list_inbox(persona, unread_only=unread)
        if not messages:
            print(f"📬 Inbox for {persona} is empty.")
            return

        # Apply limit if specified
        if limit and limit > 0:
            messages = messages[:limit]

        print(f"📬 Messages for {persona}:")
        for msg in messages:
            status = "[ NEW ]" if not msg["read"] else "[READ ]"
            print(f"{status} {msg['key']} | From: {msg['from']} | Subject: {msg['subject']}")
    except Exception as e:
        print(f"❌ Error accessing inbox: {e}")
        raise typer.Exit(code=1)

@app.command()
@log_tool_command(prefix="email")
def read(
    key: str = typer.Argument(
        ..., 
        help="The Unique Key of the message."
    ),
    persona: str = typer.Option(
        None, "--persona", "-p", 
        help="Persona ID (defaults to active session)"
    )
):
    """
    📖 READ MESSAGE.
    Retrieve and display the contents of a specific message.
    """
    if not persona:
        persona = os.environ.get("JULES_PERSONA")
        if not persona:
            persona = _get_active_persona_from_session()

    if not persona:
        print("❌ Error: Persona ID required. Please login.")
        raise typer.Exit(code=1)
        
    try:
        msg = get_message(persona, key)
        mark_read(persona, key)
        
        from rich import print as rprint
        from rich.panel import Panel
        from rich.markdown import Markdown

        content = f"**From:** {msg['from']}\n"
        content += f"**Subject:** {msg['subject']}\n"
        content += f"**Date:** {msg['date']}\n"
        content += "---\n\n"
        content += msg["body"]

        rprint(Panel(Markdown(content), title=f"Message: {key}", subtitle="JULES Internal Communication"))
    except Exception as e:
        print(f"❌ Error reading message: {e}")
        raise typer.Exit(code=1)

@app.command()
@log_tool_command(prefix="email")
def archive(
    key: str = typer.Argument(..., help="Message ID to archive."),
    persona: str = typer.Option(None, "--persona", "-p", help="Persona ID")
):
    """
    📦 ARCHIVE MESSAGE.
    Move a message to the archive directory.
    """
    if not persona: persona = _get_active_persona_from_session()
    if not persona: raise typer.Exit(code=1)
    _get_backend().archive(persona, key)
    print(f"✅ Message {key} archived.")

@app.command()
@log_tool_command(prefix="email")
def unarchive(
    key: str = typer.Argument(..., help="Message ID to unarchive."),
    persona: str = typer.Option(None, "--persona", "-p", help="Persona ID")
):
    """
    📤 UNARCHIVE MESSAGE.
    Restore a message from the archive to the inbox.
    """
    if not persona: persona = _get_active_persona_from_session()
    if not persona: raise typer.Exit(code=1)
    _get_backend().unarchive(persona, key)
    print(f"✅ Message {key} unarchived.")

@app.command()
@log_tool_command(prefix="email")
def trash(
    key: str = typer.Argument(..., help="Message ID to trash."),
    persona: str = typer.Option(None, "--persona", "-p", help="Persona ID")
):
    """
    🗑️ TRASH MESSAGE.
    Move a message to the trash directory.
    """
    if not persona: persona = _get_active_persona_from_session()
    if not persona: raise typer.Exit(code=1)
    _get_backend().trash(persona, key)
    print(f"✅ Message {key} moved to trash.")

@app.command()
@log_tool_command(prefix="email")
def restore(
    key: str = typer.Argument(..., help="Message ID to restore."),
    persona: str = typer.Option(None, "--persona", "-p", help="Persona ID")
):
    """
    ♻️ RESTORE MESSAGE.
    Recover a message from the trash.
    """
    if not persona: persona = _get_active_persona_from_session()
    if not persona: raise typer.Exit(code=1)
    _get_backend().restore(persona, key)
    print(f"✅ Message {key} restored.")

@app.command()
@log_tool_command(prefix="email")
def tag(
    action: str = typer.Argument(..., help="add, remove, or list"),
    key: str = typer.Argument(..., help="Message ID"),
    tag_name: Optional[str] = typer.Argument(None, help="Tag name"),
    persona: str = typer.Option(None, "--persona", "-p", help="Persona ID")
):
    """
    🏷️ MANAGE TAGS.
    Apply or remove metadata tags from messages.
    """
    if not persona: persona = _get_active_persona_from_session()
    if not persona: raise typer.Exit(code=1)
    
    backend = _get_backend()
    if action == "add":
        if not tag_name:
            print("Error: Tag name required for 'add' action.")
            raise typer.Exit(code=1)
        backend.tag_add(persona, key, tag_name)
        print(f"✅ Tag '{tag_name}' added to {key}.")
    elif action == "remove":
        if not tag_name:
            print("Error: Tag name required for 'remove' action.")
            raise typer.Exit(code=1)
        backend.tag_remove(persona, key, tag_name)
        print(f"✅ Tag '{tag_name}' removed from {key}.")
    elif action == "list":
        tags = backend.list_tags(persona, key)
        print(f"🏷️ Tags for {key}: {', '.join(tags)}")
    else:
        print(f"Unknown action: {action}")
        raise typer.Exit(code=1)

@app.command()
@log_tool_command(prefix="email")
def sync():
    """
    🔄 SYNC WITH GITHUB.
    Bridge local 'franklin' mail with GitHub Issues.
    Used by the 'mh' persona to facilitate user communication.
    """
    try:
        run_sync()
    except Exception as e:
        console.print(f"[bold red]❌ Sync Failed:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
