"""Domain-level exceptions for core."""


class DomainError(Exception):
    """Base class for all core domain errors."""


class WrongPhase(DomainError):
    """An operation was called in the wrong GamePhase."""


class InvalidMove(DomainError):
    """The supplied Move is not among engine.available_moves()."""


class DuplicatePlayer(DomainError):
    """Two players share the same name or the same color."""
