"""Custom exceptions for Jules."""

class JulesError(Exception):
    """Base class for all Jules-related errors."""
    pass

class SchedulerError(JulesError):
    """Base class for scheduler errors."""
    pass

class BranchError(SchedulerError):
    """Raised when branch operations fail."""
    pass

class MergeError(SchedulerError):
    """Raised when PR merging fails."""
    pass

class GitHubError(JulesError):
    """Raised when GitHub API operations fail."""
    pass

class TeamClientError(JulesError):
    """Raised when Jules API operations fail."""
    pass


class AuthenticationError(JulesError):
    """Raised when authentication is required but not provided."""
    pass
