import re
from typing import List, Dict, Any, Optional
from repo.features.mail import _get_backend, send_message
from repo.core.github import GitHubClient, get_repo_info

class MailHandler:
    """Manages the bridge between JULES local mail and GitHub Issues."""

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.gh = GitHubClient()
        self.backend = _get_backend()
        self.user_persona_id = "franklin"
        self.user_email = "franklinbaldo@gmail.com"
        # Both "franklin" and the email are treated as user identities for sync
        self.user_identities = [self.user_persona_id, self.user_email]
        self.sync_tag = "synced-to-github"
        self.issue_tag_prefix = "issue-"
        self.reply_tag_prefix = "replied-comment-"

    def sync_local_to_github(self):
        """Synchronize unread/unsynced emails for user identities to GitHub issues."""
        for user_id in self.user_identities:
            messages = self.backend.list_inbox(user_id)
            
            for msg in messages:
                tags = self.backend.list_tags(user_id, msg["key"])
                if self.sync_tag in tags:
                    continue

                # This is a new message for the User
                title = f"[PERSONA MAIL] {msg['subject']}"
                body = (
                    f"**To**: {user_id}\n"
                    f"**From**: {msg['from_id'] if 'from_id' in msg else msg.get('from', 'unknown')}\n"
                    f"**Subject**: {msg['subject']}\n"
                    f"**Date**: {msg['date']}\n\n"
                    "---\n\n"
                    f"{msg.get('body', '(no body)')}\n\n"
                    "---\n"
                    "*Reply to this issue to send a message back to the persona.*"
                )

                print(f"🚀 Syncing local message {msg['key']} (for {user_id}) to GitHub...")
                issue = self.gh.create_issue(self.owner, self.repo, title, body, labels=["persona-mail"])
                
                if issue:
                    issue_number = issue["number"]
                    self.backend.tag_add(user_id, msg["key"], self.sync_tag)
                    self.backend.tag_add(user_id, msg["key"], f"{self.issue_tag_prefix}{issue_number}")
                    print(f"✅ Created GitHub Issue #{issue_number} for local message {msg['key']}")

    def sync_github_to_local(self):
        """Fetch replies from GitHub issue comments and deliver to personas."""
        for user_id in self.user_identities:
            messages = self.backend.list_inbox(user_id)
            
            for msg in messages:
                tags = self.backend.list_tags(user_id, msg["key"])
                if self.sync_tag not in tags:
                    continue

                # Find the issue number from tags
                issue_number = None
                for tag in tags:
                    if tag.startswith(self.issue_tag_prefix):
                        issue_number = int(tag.replace(self.issue_tag_prefix, ""))
                        break
                
                if not issue_number:
                    continue

                # Fetch comments for this issue
                comments = self.gh.list_issue_comments(self.owner, self.repo, issue_number)
                
                for comment in comments:
                    comment_id = str(comment["id"])
                    # We only care about comments from the user (Franklin/repo owner usually)
                    # and only if we haven't delivered them yet.
                    
                    comment_author = comment["user"]["login"]
                    if comment_author.endswith("[bot]"):
                        continue

                    reply_tag = f"{self.reply_tag_prefix}{comment_id}"
                    if reply_tag in tags:
                        continue

                    # Deliver the reply
                    original_sender = msg.get("from_id") or msg.get("from")
                    if not original_sender:
                        print(f"⚠️ Could not determine sender for message {msg['key']}")
                        continue

                    subject = f"Re: {msg['subject']}"
                    body = (
                        f"--- Reply from {comment_author} via GitHub Issue #{issue_number} ---\n\n"
                        f"{comment['body']}"
                    )

                    print(f"📬 Delivering GitHub reply (Comment {comment_id}) to {original_sender}...")
                    send_message(
                        from_id=user_id,
                        to_id=original_sender,
                        subject=subject,
                        body=body
                    )

                    # Mark as delivered by adding a tag to the ORIGINAL message in Franklin's inbox
                    self.backend.tag_add(user_id, msg["key"], reply_tag)
                    print(f"✅ Reply delivered.")

def run_sync():
    """Main entry point for the sync process."""
    repo_info = get_repo_info()
    owner = repo_info["owner"]
    repo = repo_info["repo"]
    
    if owner == "unknown" or repo == "unknown":
        print("❌ Could not determine GitHub repository info.")
        return

    handler = MailHandler(owner, repo)
    print("🔄 Starting Local -> GitHub sync...")
    handler.sync_local_to_github()
    print("🔄 Starting GitHub -> Local sync...")
    handler.sync_github_to_local()
    print("✨ Sync complete.")
