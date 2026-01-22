"""Custom exceptions for Jules."""


class JulesError(Exception):
    """Base class for all Jules-related errors."""


class SchedulerError(JulesError):
    """Base class for scheduler errors."""


class BranchError(SchedulerError):
    """Raised when branch operations fail."""


class MergeError(SchedulerError):
    """Raised when PR merging fails."""


class GitHubError(JulesError):
    """Raised when GitHub API operations fail."""


class TeamClientError(JulesError):
    """Raised when Jules API operations fail."""
