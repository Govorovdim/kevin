class AppError(Exception):
    """Base class for application exceptions."""


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""


class AuthenticationError(AppError):
    """Raised when authentication fails (bad credentials, invalid token)."""


class AuthorizationError(AppError):
    """Raised when the user lacks permission for the requested action."""
