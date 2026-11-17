import pytest

from app.core.errors import BusinessRuleError
from app.core.validation import raise_if_invalid


def test_without_errors_does_not_raise():
    raise_if_invalid([])


def test_with_errors_responds_422_with_all_messages_together():
    with pytest.raises(BusinessRuleError) as raised:
        raise_if_invalid(["Primer error.", "Segundo error."])

    assert raised.value.status_code == 422
    assert raised.value.message == "Primer error. Segundo error."
