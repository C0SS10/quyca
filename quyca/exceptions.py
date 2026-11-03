class ConflictException(Exception):
    """The change collides with existing data (the email or institution already has a user). HTTP 409."""


class ForbiddenException(Exception):
    """The session is valid but may not do this (not admin, another user's account, deactivated). HTTP 403."""


class InvalidParamException(Exception):
    """A request parameter (query string or path) has an invalid value. Answered with HTTP 400."""


class NotEntityException(Exception):
    pass


class ProjectFileException(Exception):
    """Archive of projects cannot be read (extension, unreadable content or without headers)."""


class UnauthorizedException(Exception):
    """There is no valid session (missing or expired token, wrong credentials). Answered with HTTP 401."""
