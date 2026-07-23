"""Mail/SMS settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestMailSettingsUpdate:
    def test_valid(self) -> None:
        from models import MailSettingsUpdate

        m = MailSettingsUpdate()
        assert m.smtp_port == 587
        assert m.smtp_tls is True
        assert m.enabled is False

    def test_smtp_port_too_low(self) -> None:
        from models import MailSettingsUpdate

        with pytest.raises(ValidationError):
            MailSettingsUpdate(smtp_port=0)

    def test_smtp_port_too_high(self) -> None:
        from models import MailSettingsUpdate

        with pytest.raises(ValidationError):
            MailSettingsUpdate(smtp_port=65536)

    def test_smtp_host_max_length(self) -> None:
        from models import MailSettingsUpdate

        with pytest.raises(ValidationError):
            MailSettingsUpdate(smtp_host="x" * 256)
