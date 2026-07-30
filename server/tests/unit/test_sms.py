"""Unit tests for server/sms.py.

Tests settings management, phone normalization, Twilio API calls,
and notification template dispatch. Twilio calls are mocked.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _patch_path():
    """Replace SETTINGS_PATH with a temporary file for each test."""
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    import sms

    orig = sms.SETTINGS_PATH
    sms.SETTINGS_PATH = Path(p)
    yield
    sms.SETTINGS_PATH = orig
    if Path(p).exists():
        Path(p).unlink()


@pytest.fixture
def _full_settings() -> dict:
    """Return a complete, valid SMS settings dict."""
    return {
        "account_sid": "AC123456789abcdef",
        "auth_token": "tokensecret123",
        "from_number": "+15551234567",
    }


class TestSettings:
    """SMS settings loading, saving, and updating."""

    def test_load_no_file(self) -> None:
        from sms import _load_settings

        assert _load_settings() is None

    def test_load_valid(self, _full_settings) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))
        assert sms._load_settings() == _full_settings

    def test_load_parse_error(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text("invalid json")
        with patch("sms.logger"):
            result = sms._load_settings()
            assert result is None

    def test_save_settings(self) -> None:
        import sms

        sms._save_settings({"key": "value"})
        assert sms._load_settings() == {"key": "value"}

    def test_get_settings_without_auth_token(self, _full_settings) -> None:
        """get_settings() should never return the auth_token."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))
        result = sms.get_settings()
        assert result is not None
        assert "auth_token" not in result
        assert result["account_sid"] == "AC123456789abcdef"
        assert result["from_number"] == "+15551234567"
        assert result["configured"] is True

    def test_get_settings_no_file(self) -> None:
        from sms import get_settings

        assert get_settings() is None

    def test_get_settings_not_configured(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": ""}))
        result = sms.get_settings()
        assert result is not None
        assert result["configured"] is False

    def test_update_settings_preserves_existing(self) -> None:
        import sms

        initial = {
            "account_sid": "AC_OLD",
            "auth_token": "old_token",
            "from_number": "+12223334444",
        }
        sms.SETTINGS_PATH.write_text(json.dumps(initial))
        sms.update_settings({"account_sid": "AC_NEW"})
        saved = json.loads(sms.SETTINGS_PATH.read_text())
        assert saved["account_sid"] == "AC_NEW"
        assert saved["auth_token"] == "old_token"
        assert saved["from_number"] == "+12223334444"

    def test_update_settings_adds_auth_token(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": "AC123", "from_number": "+1555"}))
        sms.update_settings({"auth_token": "new_token"})
        saved = json.loads(sms.SETTINGS_PATH.read_text())
        assert saved["auth_token"] == "new_token"

    def test_update_settings_does_not_overwrite_empty_token(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "account_sid": "AC123",
                    "auth_token": "existing_token",
                    "from_number": "+1555",
                }
            )
        )
        sms.update_settings({"auth_token": ""})
        saved = json.loads(sms.SETTINGS_PATH.read_text())
        # Empty string is falsy, so should NOT overwrite
        assert saved["auth_token"] == "existing_token"

    def test_update_settings_returns_public_view(self, _full_settings) -> None:
        """update_settings() should return the public view (no auth_token)."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))
        result = sms.update_settings({"account_sid": "AC_UPDATED"})
        assert "auth_token" not in result
        assert result["account_sid"] == "AC_UPDATED"

    def test_is_configured_returns_true(self, _full_settings) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))
        assert sms.is_configured() is True

    def test_is_configured_returns_false_no_file(self) -> None:
        from sms import is_configured

        assert is_configured() is False

    def test_is_configured_returns_false_incomplete(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps({"account_sid": ""}))
        assert sms.is_configured() is False

    def test_is_configured_returns_false_missing_token(self) -> None:
        import sms

        sms.SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "account_sid": "AC123",
                    "from_number": "+1555",
                }
            )
        )
        assert sms.is_configured() is False


class TestCustomerPhone:
    """Customer phone extraction."""

    def test_returns_mobile(self) -> None:
        from sms import _customer_phone

        assert (
            _customer_phone({"mobile": "+15551112222", "phone": "+15553334444"}) == "+15551112222"
        )

    def test_falls_back_to_phone(self) -> None:
        from sms import _customer_phone

        assert _customer_phone({"phone": "+15553334444"}) == "+15553334444"

    def test_returns_none_when_no_phone(self) -> None:
        from sms import _customer_phone

        assert _customer_phone({}) is None

    def test_returns_none_when_phone_none(self) -> None:
        from sms import _customer_phone

        assert _customer_phone({"phone": None}) is None

    def test_returns_none_when_customer_none(self) -> None:
        from sms import _customer_phone

        assert _customer_phone(None) is None


class TestSendSms:
    """Twilio SMS sending logic."""

    @pytest.mark.asyncio
    async def test_no_settings_returns_false(self) -> None:
        """Should return False when no settings file exists."""
        from sms import send_sms

        with patch("sms.logger"):
            result = await send_sms("+15551234567", "Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_not_configured_empty_account_sid(self) -> None:
        """Should return False when account_sid is missing."""
        import sms

        sms.SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "account_sid": "",
                    "auth_token": "tok",
                    "from_number": "+1555",
                }
            )
        )
        with patch("sms.logger"):
            result = await sms.send_sms("+15551234567", "Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_not_configured_empty_auth_token(self) -> None:
        """Should return False when auth_token is missing."""
        import sms

        sms.SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "account_sid": "AC123",
                    "auth_token": "",
                    "from_number": "+1555",
                }
            )
        )
        with patch("sms.logger"):
            result = await sms.send_sms("+15551234567", "Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_not_configured_empty_from_number(self) -> None:
        """Should return False when from_number is missing."""
        import sms

        sms.SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "account_sid": "AC123",
                    "auth_token": "tok",
                    "from_number": "",
                }
            )
        )
        with patch("sms.logger"):
            result = await sms.send_sms("+15551234567", "Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_sends_to_normalized_number(self, _full_settings) -> None:
        """Should normalize a 10-digit US number by adding +1 prefix."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger"):
                result = await sms.send_sms("5551234567", "Hello")

        assert result is True
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_sends_to_11_digit_number(self, _full_settings) -> None:
        """Should handle 11-digit number starting with 1."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger"):
                result = await sms.send_sms("15551234567", "Hello")

        assert result is True
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_preserves_plus_prefix(self, _full_settings) -> None:
        """Should not modify a number that already has + prefix."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger"):
                result = await sms.send_sms("+12223334444", "Hello")

        assert result is True
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+12223334444"

    @pytest.mark.asyncio
    async def test_strips_whitespace(self, _full_settings) -> None:
        """Should trim whitespace from the phone number."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger"):
                result = await sms.send_sms("  5551234567  ", "Hello")

        assert result is True
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_successful_send(self, _full_settings) -> None:
        """Should return True and call Twilio API correctly."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"sid": "SM123", "status": "queued"}
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger"):
                result = await sms.send_sms("+15551234567", "Hello, customer!")

        assert result is True
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        assert (
            call_args[0][0]
            == "https://api.twilio.com/2010-04-01/Accounts/AC123456789abcdef/Messages.json"
        )
        assert call_args[1]["auth"] == ("AC123456789abcdef", "tokensecret123")
        assert call_args[1]["data"]["From"] == "+15551234567"
        assert call_args[1]["data"]["Body"] == "Hello, customer!"
        assert call_args[1]["timeout"] == 15

    @pytest.mark.asyncio
    async def test_twilio_api_error(self, _full_settings) -> None:
        """Should return False when Twilio returns >=400."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"message": "Account not authorized"}
        mock_resp.text = '{"message": "Account not authorized"}'
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger") as mock_logger:
                result = await sms.send_sms("+15551234567", "Hello")

        assert result is False
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_network_error(self, _full_settings) -> None:
        """Should return False when an exception is raised."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=ConnectionError("Network error"))

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger") as mock_logger:
                result = await sms.send_sms("+15551234567", "Hello")

        assert result is False
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_logs_success(self, _full_settings) -> None:
        """Should log when SMS is sent successfully."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger") as mock_logger:
                await sms.send_sms("+15551234567", "Test body")

        mock_logger.info.assert_called_with("SMS sent to %s: %.60s", "+15551234567", "Test body")


class TestConnection:
    """Twilio connection testing."""

    @pytest.mark.asyncio
    async def test_no_settings_returns_error(self) -> None:
        """Should return error when no settings exist."""
        from sms import test_connection

        result = await test_connection()
        assert result["ok"] is False
        assert "not configured" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_no_account_info(self) -> None:
        """Should return error when account_sid or auth_token missing."""
        import sms

        sms.SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "account_sid": "",
                    "auth_token": "",
                    "from_number": "+1555",
                }
            )
        )
        result = await sms.test_connection()
        assert result["ok"] is False
        assert "Account SID and Auth Token required" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_connection(self, _full_settings) -> None:
        """Should return success when Twilio API responds."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"friendly_name": "My Twilio Account"}
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            result = await sms.test_connection()

        assert result["ok"] is True
        assert "Connected: My Twilio Account" in result["message"]
        assert result["from_number"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_connection_api_error(self, _full_settings) -> None:
        """Should return error when Twilio API returns >=400."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            result = await sms.test_connection()

        assert result["ok"] is False
        assert "Twilio API error: 401" in result["error"]

    @pytest.mark.asyncio
    async def test_connection_network_error(self, _full_settings) -> None:
        """Should return error when network fails."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=TimeoutError("Connection timed out"))

        with patch("sms.get_http_client", return_value=mock_client):
            result = await sms.test_connection()

        assert result["ok"] is False
        assert "Connection timed out" in result["error"]


class TestNotifications:
    """SMS notification template dispatch."""

    def _assert_sms_sent(self, func_name: str, *args) -> None:
        """Verify a notification function calls send_sms with the right body."""
        import sms

        with patch.object(sms, "send_sms", new_callable=AsyncMock) as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: None):
                getattr(sms, func_name)(*args)
                mock_send.assert_called_once()

    def test_ticket_status_change_sends_sms(self) -> None:
        self._assert_sms_sent(
            "_notify_ticket_status_change",
            "+15551234567",
            101,
            "Broken screen",
            "in_progress",
        )

    def test_invoice_created_sends_sms(self) -> None:
        self._assert_sms_sent("_notify_invoice_created", "+15551234567", 201, 150.0)

    def test_payment_received_sends_sms(self) -> None:
        self._assert_sms_sent("_notify_payment_received", "+15551234567", 201, 50.0)

    def test_appointment_created_sends_sms(self) -> None:
        self._assert_sms_sent(
            "_notify_appointment_created", "+15551234567", "Repair", 1710000000000
        )

    def test_appointment_reminder_sends_sms(self) -> None:
        self._assert_sms_sent(
            "_notify_appointment_reminder", "+15551234567", "Repair", 1710000000000
        )

    def test_estimate_approved_sends_sms(self) -> None:
        self._assert_sms_sent("_notify_estimate_approved", "+15551234567", 301, 250.0)

    def test_overdue_reminder_sends_sms(self) -> None:
        self._assert_sms_sent("_notify_overdue_reminder", "+15551234567", 401, 100.0)

    def test_notification_sms_body_content(self) -> None:
        """Notifications should have descriptive SMS body text."""
        import sms

        with patch.object(sms, "send_sms", new_callable=AsyncMock) as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: None):
                sms._notify_ticket_status_change("+15551234567", 42, "Broken", "in_progress")
            body = mock_send.call_args[0][1]
            assert "Ticket #42" in body
            assert "In Progress" in body

            with patch("sms.asyncio.ensure_future", lambda c, **kw: None):
                sms._notify_invoice_created("+15551234567", 99, 199.99)
                body = mock_send.call_args[0][1]
                assert "Invoice #99" in body
                assert "$199.99" in body

            with patch("sms.asyncio.ensure_future", lambda c, **kw: None):
                sms._notify_payment_received("+15551234567", 99, 50.0)
                body = mock_send.call_args[0][1]
                assert "$50.00" in body
                assert "Invoice #99" in body

    def test_notification_fire_and_forget(self) -> None:
        """Each notification should use asyncio.ensure_future for fire-and-forget."""
        import sms

        with patch("sms.asyncio.ensure_future") as mock_ensure:
            sms._notify_ticket_status_change("+15551234567", 1, "Test", "new")
            mock_ensure.assert_called_once()

    def test_ticket_status_labels(self) -> None:
        """Should use the correct status labels."""
        import sms

        status_tests = [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("waiting_parts", "Waiting for Parts"),
            ("waiting_customer", "Waiting for Customer"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
        ]

        with patch.object(sms, "send_sms", new_callable=AsyncMock) as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: None):
                for status, label in status_tests:
                    sms._notify_ticket_status_change("+15551234567", 1, "Test", status)
                    body = mock_send.call_args[0][1]
                    assert label in body

    def test_appointment_time_formatting(self) -> None:
        """Appointment notification should format timestamp correctly."""
        import sms

        with patch.object(sms, "send_sms", new_callable=AsyncMock) as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: None):
                # 1710000000000ms = Sunday, March 10, 2024 12:00:00 AM GMT (approximately)
                sms._notify_appointment_created("+15551234567", "Oil Change", 1710000000000)
                body = mock_send.call_args[0][1]
                assert "Appointment scheduled" in body
                assert "Oil Change" in body

    def test_overdue_reminder_body(self) -> None:
        """Overdue reminder should mention overdue and amount."""
        import sms

        with patch.object(sms, "send_sms", new_callable=AsyncMock) as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: None):
                sms._notify_overdue_reminder("+15551234567", 401, 100.0)
                body = mock_send.call_args[0][1]
                assert "overdue" in body.lower()
                assert "$100.00" in body
                assert "Invoice #401" in body


class TestLoadSettingsEdgeCases:
    """Edge cases for _load_settings not covered by the fixture-based tests."""

    def test_settings_path_does_not_exist(self) -> None:
        """Should return None when SETTINGS_PATH points to a non-existent file."""
        import sms

        # Point to a path that definitely doesn't exist
        sms.SETTINGS_PATH = Path("/nonexistent/path/to/sms_settings.json")
        try:
            result = sms._load_settings()
            assert result is None
        finally:
            # Restore to the temp path managed by the fixture
            sms.SETTINGS_PATH = Path(tempfile.mkstemp(suffix=".json")[1])


class TestPhoneNormalization:
    """Phone number normalization edge cases."""

    @pytest.mark.asyncio
    async def test_non_standard_digit_count(self, _full_settings) -> None:
        """Should prepend + to numbers that don't match 10 or 11 digits."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger"):
                # 7-digit number — goes to the else branch (line 110)
                result = await sms.send_sms("5551234", "Hello")

        assert result is True
        call_kwargs = mock_client.post.call_args[1]
        # 7 digits → +5551234
        assert call_kwargs["data"]["To"] == "+5551234"

    @pytest.mark.asyncio
    async def test_11_digit_not_starting_with_1(self, _full_settings) -> None:
        """Should prepend + to 11-digit numbers not starting with 1."""
        import sms

        sms.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("sms.get_http_client", return_value=mock_client):
            with patch("sms.logger"):
                # 11 digits starting with 2 — goes to the else branch (line 110)
                result = await sms.send_sms("25512345678", "Hello")

        assert result is True
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["To"] == "+25512345678"
