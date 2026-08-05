"""Tests for sms module (Twilio SMS sending with JSON settings)."""

import json
from unittest.mock import AsyncMock, Mock, patch, mock_open

import pytest

from sms import (
    _load_settings, _save_settings, get_settings, update_settings,
    is_configured, _customer_phone, send_sms,
    _notify_ticket_status_change, _notify_invoice_created,
    _notify_payment_received, _notify_appointment_created,
    _notify_appointment_reminder, _notify_estimate_approved, _notify_overdue_reminder,
)


class TestLoadSettings:
    def test_returns_none_when_file_missing(self):
        with patch("pathlib.Path.exists", return_value=False):
            assert _load_settings() is None

    def test_returns_json_when_exists(self):
        data = {"account_sid": "ACxxx", "auth_token": "token123"}
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(data))):
                assert _load_settings() == data

    def test_returns_none_on_corrupt_json(self):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="bad json")):
                assert _load_settings() is None


class TestSaveSettings:
    def test_writes_json_to_file(self):
        data = {"account_sid": "ACxxx"}
        with patch("pathlib.Path.write_text") as mock_write:
            _save_settings(data)
            written = json.loads(mock_write.call_args[0][0])
            assert written["account_sid"] == "ACxxx"

    def test_logs_on_save(self):
        with patch("pathlib.Path.write_text"):
            with patch("sms.logger.info") as mock_log:
                _save_settings({"a": "b"})
                mock_log.assert_called_once()


class TestGetSettings:
    def test_returns_none_when_no_settings(self):
        with patch("sms._load_settings", return_value=None):
            assert get_settings() is None

    def test_returns_safe_fields(self):
        with patch("sms._load_settings", return_value={
            "account_sid": "ACxxx", "auth_token": "token", "from_number": "+15551234567",
        }):
            result = get_settings()
            assert "account_sid" in result
            assert "from_number" in result
            assert "auth_token" not in result

    def test_configured_flag_true(self):
        with patch("sms._load_settings", return_value={
            "account_sid": "ACxxx", "auth_token": "secret", "from_number": "+15551234567",
        }):
            result = get_settings()
            assert result["configured"] is True

    def test_configured_flag_false(self):
        with patch("sms._load_settings", return_value={"account_sid": "ACxxx"}):
            result = get_settings()
            assert result["configured"] is False


class TestUpdateSettings:
    def test_merges_with_existing(self):
        with patch("sms._load_settings", return_value={"account_sid": "ACold", "from_number": "+1"}):
            with patch("sms._save_settings") as mock_save:
                update_settings({"account_sid": "ACnew"})
                args = mock_save.call_args[0][0]
                assert args["account_sid"] == "ACnew"
                assert args["from_number"] == "+1"

    def test_preserves_auth_token_when_not_in_update(self):
        with patch("sms._load_settings", return_value={"auth_token": "old"}):
            with patch("sms._save_settings") as mock_save:
                update_settings({})
                args = mock_save.call_args[0][0]
                # auth_token is preserved from loaded settings
                assert args["auth_token"] == "old"

    def test_updates_auth_token_when_provided(self):
        with patch("sms._load_settings", return_value={"auth_token": "old"}):
            with patch("sms._save_settings") as mock_save:
                update_settings({"auth_token": "newtoken"})
                args = mock_save.call_args[0][0]
                assert args["auth_token"] == "newtoken"


class TestIsConfigured:
    def test_returns_false_when_no_settings(self):
        with patch("sms._load_settings", return_value=None):
            assert is_configured() is False

    def test_returns_true_when_all_fields_present(self):
        with patch("sms._load_settings", return_value={
            "account_sid": "ACx", "auth_token": "t", "from_number": "+1",
        }):
            assert is_configured() is True

    def test_returns_false_when_missing_field(self):
        with patch("sms._load_settings", return_value={"account_sid": "ACx"}):
            assert is_configured() is False


class TestCustomerPhone:
    def test_returns_mobile_preferred(self):
        assert _customer_phone({"mobile": "555-1111", "phone": "555-2222"}) == "555-1111"

    def test_falls_back_to_phone(self):
        assert _customer_phone({"phone": "555-2222"}) == "555-2222"

    def test_returns_none_when_no_customer(self):
        assert _customer_phone(None) is None

    def test_returns_none_when_no_phone(self):
        assert _customer_phone({"email": "a@b.com"}) is None


class TestSendSms:
    @pytest.mark.asyncio
    async def test_returns_false_when_not_configured(self):
        with patch("sms._load_settings", return_value=None):
            assert await send_sms("+15551234567", "Hello") is False

    @pytest.mark.asyncio
    async def test_returns_false_when_settings_incomplete(self):
        with patch("sms._load_settings", return_value={"account_sid": "ACx"}):
            assert await send_sms("+15551234567", "Hello") is False

    @pytest.mark.asyncio
    async def test_sends_via_twilio_api(self):
        settings = {"account_sid": "ACxxx", "auth_token": "token", "from_number": "+15550001111"}
        mock_client = AsyncMock()
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_client.post.return_value = mock_resp

        with patch("sms._load_settings", return_value=settings):
            with patch("sms.get_http_client", return_value=mock_client):
                result = await send_sms("+15551234567", "Test message")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args[1]
        assert call_args["data"]["From"] == "+15550001111"
        assert call_args["data"]["To"] == "+15551234567"
        assert call_args["data"]["Body"] == "Test message"

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        settings = {"account_sid": "ACx", "auth_token": "t", "from_number": "+15550001111"}
        mock_client = AsyncMock()
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"message": "Authenticate"}
        mock_client.post.return_value = mock_resp

        with patch("sms._load_settings", return_value=settings):
            with patch("sms.get_http_client", return_value=mock_client):
                result = await send_sms("+15551234567", "Test")

        assert result is False

    @pytest.mark.asyncio
    async def test_normalizes_us_number(self):
        settings = {"account_sid": "ACx", "auth_token": "t", "from_number": "+15550001111"}
        mock_client = AsyncMock()
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_client.post.return_value = mock_resp

        with patch("sms._load_settings", return_value=settings):
            with patch("sms.get_http_client", return_value=mock_client):
                result = await send_sms("5551234567", "Hello")

        assert result is True
        call_args = mock_client.post.call_args[1]
        # 10-digit US number gets +1 prefix
        assert call_args["data"]["To"] == "+15551234567"


class TestTestConnection:
    @pytest.mark.asyncio
    async def test_returns_ok_false_when_not_configured(self):
        from sms import test_connection
        with patch("sms._load_settings", return_value=None):
            result = await test_connection()
            assert result == {"ok": False, "error": "SMS not configured"}

    @pytest.mark.asyncio
    async def test_returns_error_when_missing_creds(self):
        from sms import test_connection
        with patch("sms._load_settings", return_value={"account_sid": "ACx"}):
            result = await test_connection()
            assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_returns_ok_on_success(self):
        from sms import test_connection
        settings = {"account_sid": "ACx", "auth_token": "t", "from_number": "+1555"}
        mock_client = AsyncMock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"friendly_name": "Test Account"}
        mock_client.get.return_value = mock_resp

        with patch("sms._load_settings", return_value=settings):
            with patch("sms.get_http_client", return_value=mock_client):
                result = await test_connection()
                assert result["ok"] is True
                assert result["message"] == "Connected: Test Account"


class TestSmsNotifications:
    def test_notify_ticket_status(self):
        with patch("sms.send_sms") as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: c):
                _notify_ticket_status_change("+15551234567", 42, "Broken", "in_progress")
                mock_send.assert_called_once_with("+15551234567", 'Ticket #42 — In Progress: "Broken"')

    def test_notify_invoice_created(self):
        with patch("sms.send_sms") as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: c):
                _notify_invoice_created("+15551234567", 101, 250.0)
                mock_send.assert_called_once()

    def test_notify_payment_received(self):
        with patch("sms.send_sms") as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: c):
                _notify_payment_received("+15551234567", 101, 100.0)
                mock_send.assert_called_once()

    def test_notify_appointment_created(self):
        with patch("sms.send_sms") as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: c):
                _notify_appointment_created("+15551234567", "Repair", 1700000000000)
                mock_send.assert_called_once()

    def test_notify_appointment_reminder(self):
        with patch("sms.send_sms") as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: c):
                _notify_appointment_reminder("+15551234567", "Checkup", 1700000000000)
                mock_send.assert_called_once()

    def test_notify_estimate_approved(self):
        with patch("sms.send_sms") as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: c):
                _notify_estimate_approved("+15551234567", 5, 500.0)
                mock_send.assert_called_once()

    def test_notify_overdue_reminder(self):
        with patch("sms.send_sms") as mock_send:
            with patch("sms.asyncio.ensure_future", lambda c, **kw: c):
                _notify_overdue_reminder("+15551234567", 42, 150.0)
                mock_send.assert_called_once()
