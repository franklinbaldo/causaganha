"""PR code review using ephemeral repoless sessions.

Uses the Jules API January 2026 repoless sessions feature to perform
PR code reviews without consuming regular session quota. Reviews can
be done for open PRs or even post-merge to catch issues.
"""

from dataclasses import dataclass

from repo.core.client import TeamClient
from repo.features.ephemeral_pool import EphemeralSessionPool


@dataclass
class ReviewResult:
    """Result of a PR review request."""

    pr_url: str
    session_id: str
    request_sent: bool
    error: str | None = None


@dataclass
class ReviewRecommendation:
    """Parsed review recommendation from the reviewer session."""

    verdict: str  # APPROVE, REQUEST_CHANGES, REVERT_RECOMMENDED
    summary: str
    issues: list[str]
    suggestions: list[str]
    fix_instructions: str | None = None


class PRReviewer:
    """PR code reviewer using ephemeral repoless sessions.

    This class enables PR code review without consuming regular session
    quota by using repoless ephemeral sessions that can be reused.

    Example usage:
        reviewer = PRReviewer(client)

        # Request a review (async - returns immediately)
        result = reviewer.request_review("https://github.com/owner/repo/pull/123")

        # Later, check for review results via activities
        # Or use webhooks/polling to get the review response

    Benefits:
    - Doesn't consume regular session quota (100/day)
    - Session can be reused for multiple PR reviews
    - Can review post-merge to catch issues
    - Returns actionable fix instructions

    """

    def __init__(self, client: TeamClient, pool: EphemeralSessionPool | None = None):
        """Initialize the PR reviewer.

        Args:
            client: TeamClient instance for Jules API calls.
            pool: Optional EphemeralSessionPool. If not provided, creates one.

        """
        self.client = client
        self.pool = pool or EphemeralSessionPool(client)

    def request_review(
        self,
        pr_url: str,
        context: str | None = None,
        post_merge: bool = False,
    ) -> ReviewResult:
        """Request a code review for a PR.

        This sends a review request to the ephemeral reviewer session.
        The review happens asynchronously - poll the session activities
        to get the review result.

        Args:
            pr_url: Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            context: Optional additional context for the review.
            post_merge: If True, indicates this is a post-merge review
                       to check for issues that should be reverted.

        Returns:
            ReviewResult with session_id and request status.

        """
        # Get or create the reviewer session
        session_id = self.pool.get_or_create_reviewer()
        if not session_id:
            return ReviewResult(
                pr_url=pr_url,
                session_id="",
                request_sent=False,
                error="Failed to get or create reviewer session",
            )

        # Build the review request message
        if post_merge:
            message = f"""## 🔍 Post-Merge Review Request

**PR URL:** {pr_url}

This PR has already been merged. Please review it for any issues that
might require a revert or follow-up fix.

**Focus Areas:**
- Security vulnerabilities introduced
- Breaking changes or regressions
- Critical bugs that need immediate attention
- Code quality issues that warrant a follow-up PR

{f"**Additional Context:** {context}" if context else ""}

Please provide:
1. Summary of what was merged
2. Any issues found that require attention
3. If REVERT_RECOMMENDED: specific revert/fix instructions
"""
        else:
            message = f"""## 🔍 PR Review Request

**PR URL:** {pr_url}

Please review this PR and provide feedback.

{f"**Additional Context:** {context}" if context else ""}

Please provide:
1. Summary of the changes
2. Any issues found (bugs, security, style)
3. Suggestions for improvement
4. Your verdict: APPROVE / REQUEST_CHANGES / REVERT_RECOMMENDED
"""

        # Send the review request
        try:
            self.client.send_message(session_id, message)
            print(f"  Sent review request for {pr_url} to session {session_id}")
            return ReviewResult(
                pr_url=pr_url,
                session_id=session_id,
                request_sent=True,
            )
        except Exception as e:
            return ReviewResult(
                pr_url=pr_url,
                session_id=session_id,
                request_sent=False,
                error=str(e),
            )

    def request_batch_review(
        self,
        pr_urls: list[str],
        context: str | None = None,
    ) -> list[ReviewResult]:
        """Request reviews for multiple PRs.

        All reviews are sent to the same reusable session.

        Args:
            pr_urls: List of GitHub PR URLs to review.
            context: Optional context that applies to all reviews.

        Returns:
            List of ReviewResult for each PR.

        """
        results = []
        for pr_url in pr_urls:
            result = self.request_review(pr_url, context=context)
            results.append(result)
        return results

    def create_fix_session_from_review(
        self,
        review: ReviewRecommendation,
        repo_info: dict[str, str],
        pr_number: int,
    ) -> str | None:
        """Create a fix session based on a review recommendation.

        If a review recommends changes or a revert, this creates a new
        regular (non-repoless) session to implement the fix.

        Args:
            review: The review recommendation with fix instructions.
            repo_info: Dict with 'owner' and 'repo' keys.
            pr_number: The PR number that was reviewed.

        Returns:
            Session ID of the fix session, or None on failure.

        """
        if review.verdict == "APPROVE":
            print("  Review verdict is APPROVE, no fix session needed")
            return None

        if not review.fix_instructions:
            print("  No fix instructions provided in review")
            return None

        # Build fix prompt
        if review.verdict == "REVERT_RECOMMENDED":
            title = f"🔄 Revert/Fix PR #{pr_number}"
            prompt = f"""# Revert/Fix Required for PR #{pr_number}

## Review Summary
{review.summary}

## Issues Found
{chr(10).join(f"- {issue}" for issue in review.issues)}

## Fix Instructions
{review.fix_instructions}

## Your Task
1. Analyze the issues identified
2. Implement the recommended fix or revert
3. Ensure tests pass after changes
4. Create a PR with clear explanation
"""
        else:  # REQUEST_CHANGES
            title = f"🔧 Fix Issues from PR #{pr_number} Review"
            prompt = f"""# Fix Issues from PR #{pr_number} Review

## Review Summary
{review.summary}

## Issues to Fix
{chr(10).join(f"- {issue}" for issue in review.issues)}

## Suggestions
{chr(10).join(f"- {s}" for s in review.suggestions)}

## Fix Instructions
{review.fix_instructions}

## Your Task
1. Address the issues identified in the review
2. Implement the suggested improvements
3. Ensure tests pass after changes
4. Create a PR with the fixes
"""

        try:
            result = self.client.create_session(
                prompt=prompt,
                owner=repo_info["owner"],
                repo=repo_info["repo"],
                branch="main",
                title=title,
                automation_mode="AUTO_CREATE_PR",
                require_plan_approval=False,
            )
            session_id = result.get("name", "").split("/")[-1]
            print(f"  Created fix session: {session_id}")
            return session_id
        except Exception as e:
            print(f"  Failed to create fix session: {e}")
            return None


def parse_review_response(response_text: str) -> ReviewRecommendation | None:
    """Parse a review response from the reviewer session.

    This is a simple parser - in production you might want to use
    structured output or a more robust parsing approach.

    Args:
        response_text: The raw response text from the reviewer session.

    Returns:
        Parsed ReviewRecommendation, or None if parsing fails.

    """
    # Look for verdict
    verdict = "REQUEST_CHANGES"  # Default
    response_upper = response_text.upper()
    if "REVERT_RECOMMENDED" in response_upper or "REVERT RECOMMENDED" in response_upper:
        verdict = "REVERT_RECOMMENDED"
    elif "APPROVE" in response_upper and "REQUEST_CHANGES" not in response_upper:
        verdict = "APPROVE"

    # Extract sections (basic parsing)
    lines = response_text.split("\n")
    summary = ""
    issues: list[str] = []
    suggestions: list[str] = []
    fix_instructions = ""

    current_section = ""
    for line in lines:
        line_lower = line.lower().strip()
        if "summary" in line_lower and line.startswith("#"):
            current_section = "summary"
        elif "issue" in line_lower and line.startswith("#"):
            current_section = "issues"
        elif "suggestion" in line_lower and line.startswith("#"):
            current_section = "suggestions"
        elif ("fix" in line_lower or "instruction" in line_lower) and line.startswith("#"):
            current_section = "fix"
        elif line.strip().startswith("-") or line.strip().startswith("*"):
            item = line.strip().lstrip("-*").strip()
            if current_section == "issues" and item:
                issues.append(item)
            elif current_section == "suggestions" and item:
                suggestions.append(item)
        elif current_section == "summary" and line.strip():
            summary += line.strip() + " "
        elif current_section == "fix" and line.strip():
            fix_instructions += line + "\n"

    return ReviewRecommendation(
        verdict=verdict,
        summary=summary.strip(),
        issues=issues,
        suggestions=suggestions,
        fix_instructions=fix_instructions.strip() if fix_instructions else None,
    )
