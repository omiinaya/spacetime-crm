"""Unit tests for server/sms.py."""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)


@pytest.fixture(autouse=True)
def _patch_path():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    import sms

    orig = sms.SETTINGS_PATH
    sms.SETTINGS_PATH = Path(p)
    yield
    sms.SETTINGS_PATH = orig
    if os.path.exists(p):
        os.unlink(p)


class TestSettings:
    def test_load_no_file(self) -> None:
        from sms import _load_settings

        assert _load_settings() is None

    def test_load_valid(self) -> None:
        import sms

        d = {"account_sid": "AC1", "auth_token": "t", "from_number": "+1"}
        sms.SETTINGS_PATH.write_text(json.dumps(d))
        assert sms._load_settings() == d

    def test_load_parse_error(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text("bad")
        with patch("sms.logger"):
            assert sms._load_settings() is None

    def test_save(self) -> None:
        import sms

        sms._save_settings({"a": "b"})
        assert sms._load_settings() == {"a": "b"}

    def test_get_not_configured(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": ""}))
        assert sms.get_settings()["configured"] is False

    def test_get_configured(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC1", "auth_token": "t", "from_number": "+1"}))
        assert sms.get_settings()["configured"] is True

    def test_get_no_file(self) -> None:
        import sms

        assert sms.get_settings() is None

    def test_update(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "old", "auth_token": "t", "from_number": "+1"}))
        r = sms.update_settings({"account_sid": "new"})
        assert r["account_sid"] == "new"

    def test_update_with_auth(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "old", "auth_token": "t", "from_number": "+1"}))
        r = sms.update_settings({"account_sid": "new", "auth_token": "newtoken"})
        assert r["account_sid"] == "new"

    def test_is_configured(self) -> None:
        import sms

        assert sms.is_configured() is False
        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "a", "auth_token": "b", "from_number": "c"}))
        assert sms.is_configured() is True


class TestPhone:
    def test_mobile(self) -> None:
        from sms import _customer_phone

        assert _customer_phone({"mobile": "+1555"}) == "+1555"

    def test_phone(self) -> None:
        from sms import _customer_phone

        assert _customer_phone({"phone": "+1556"}) == "+1556"

    def test_none(self) -> None:
        from sms import _customer_phone

        assert _customer_phone(None) is None
        assert _customer_phone({}) is None


class TestSend:
    @pytest.mark.asyncio
    async def test_not_configured(self) -> None:
        from sms import send_sms

        assert await send_sms("+1", "hi") is False

    @pytest.mark.asyncio
    async def test_incomplete_settings(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC1"}))
        assert await sms.send_sms("+1", "hi") is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC1", "auth_token": "t", "from_number": "+1"}))
        import client

        client._shared_client.post = AsyncMock(return_value=MagicMock(status_code=201, json=lambda: {"sid": "S1"}))
        result = await sms.send_sms("+1555", "hi")
        assert result is True

    @pytest.mark.asyncio
    async def test_failure(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC1", "auth_token": "t", "from_number": "+1"}))
        import client

        client._shared_client.post = AsyncMock(
            return_value=MagicMock(status_code=400, text="bad", json=lambda: {"message": "err"}),
        )
        with patch("sms.logger"):
            result = await sms.send_sms("+1555", "hi")
            assert result is False

    @pytest.mark.asyncio
    async def test_phone_normalization_10_digit(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC1", "auth_token": "t", "from_number": "+1"}))
        import client

        client._shared_client.post = AsyncMock(return_value=MagicMock(status_code=201, json=lambda: {"sid": "S1"}))
        await sms.send_sms("5551234567", "hi")  # 10-digit US number
        # Should normalize to +15551234567
        call_kwargs = client._shared_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_phone_normalization_11_digit(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC1", "auth_token": "t", "from_number": "+1"}))
        import client

        client._shared_client.post = AsyncMock(return_value=MagicMock(status_code=201, json=lambda: {"sid": "S1"}))
        await sms.send_sms("15551234567", "hi")
        call_kwargs = client._shared_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_phone_normalization_already_plus(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC1", "auth_token": "t", "from_number": "+1"}))
        import client

        client._shared_client.post = AsyncMock(return_value=MagicMock(status_code=201, json=lambda: {"sid": "S1"}))
        await sms.send_sms("+15551234567", "hi")
        call_kwargs = client._shared_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+15551234567"


class TestNotifications:
    def _check(self, func, *a) -> None:
        import sms

        with patch.object(sms, "send_sms", new_callable=AsyncMock) as m:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                func(*a)
                loop.run_until_complete(asyncio.sleep(0.02))
                m.assert_awaited_once()
            finally:
                loop.close()

    def test_ticket_status(self) -> None:
        from sms import _notify_ticket_status_change

        self._check(_notify_ticket_status_change, "+1", 1, "open", "t")

    def test_invoice_created(self) -> None:
        from sms import _notify_invoice_created

        self._check(_notify_invoice_created, "+1", 1, 10.0)

    def test_payment_received(self) -> None:
        from sms import _notify_payment_received

        self._check(_notify_payment_received, "+1", 1, 10.0)

    def test_appt_created(self) -> None:
        from sms import _notify_appointment_created

        self._check(_notify_appointment_created, "+1", "meet", 1700000000000)

    def test_appt_reminder(self) -> None:
        from sms import _notify_appointment_reminder

        self._check(_notify_appointment_reminder, "+1", "meet", 1700000000000)

    def test_estimate(self) -> None:
        from sms import _notify_estimate_approved

        self._check(_notify_estimate_approved, "+1", 1, 10.0)

    def test_overdue(self) -> None:
        from sms import _notify_overdue_reminder

        self._check(_notify_overdue_reminder, "+1", 1, 10.0)
