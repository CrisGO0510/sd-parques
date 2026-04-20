import pytest
from core.exceptions import (
    DomainError, WrongPhase, InvalidMove, DuplicatePlayer,
)


def test_domain_error_is_exception():
    assert issubclass(DomainError, Exception)


def test_all_domain_errors_inherit_from_domain_error():
    assert issubclass(WrongPhase, DomainError)
    assert issubclass(InvalidMove, DomainError)
    assert issubclass(DuplicatePlayer, DomainError)


def test_errors_can_be_raised_with_message():
    with pytest.raises(WrongPhase, match="not in SETUP"):
        raise WrongPhase("not in SETUP")
