"""
Tests for server/sms.py.

Tests Twilio SMS configuration, sending, and notification templates.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.sms import (
    _customer_phone,
    _load_settings,
    _notify_appointment_created,
    _notify_appointment_reminder,
    _notify_estimate_approved,
    _notify_invoice_created,
    _notify_overdue_reminder,
    _notify_payment_received,
    _notify_ticket_status_change,
    _save_settings,
    get_settings,
    is_configured,
    send_sms,
    update_settings,
)
from server.sms import (
    test_connection as _sms_test_connection,
)


class TestSms:
    """Test suite for sms.py."""

    def test_load_settings_no_file(self, tmp_path):
        with patch("server.sms.SETTINGS_PATH", tmp_path / "nonexistent.json"):
            assert _load_settings() is None

    def test_load_settings_success(self, tmp_path):
        settings_file = tmp_path / "sms_settings.json"
        test_data = {"account_sid": "AC123", "from_number": "+15551234567"}
        settings_file.write_text(json.dumps(test_data))
        with patch("server.sms.SETTINGS_PATH", settings_file):
            result = _load_settings()
            assert result["account_sid"] == "AC123"

    def test_load_settings_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        with patch("server.sms.SETTINGS_PATH", bad_file):
            assert _load_settings() is None

    def test_save_settings_writes(self, tmp_path):
        output = tmp_path / "out.json"
        with patch("server.sms.SETTINGS_PATH", output):
            _save_settings({"account_sid": "AC123"})
            assert output.exists()

    def test_get_settings_strips_auth_token(self):
        with patch(
            "server.sms._load_settings",
            return_value={
                "account_sid": "AC123",
                "auth_token": "secret",
                "from_number": "+1555",
            },
        ):
            result = get_settings()
            assert "auth_token" not in result

    def test_get_settings_no_settings(self):
        with patch("server.sms._load_settings", return_value=None):
            assert get_settings() is None

    def test_is_configured_returns_false_when_missing(self):
        with patch("server.sms._load_settings", return_value=None):
            assert is_configured() is False

    def test_is_configured_returns_false_when_incomplete(self):
        with patch("server.sms._load_settings", return_value={"account_sid": "AC123"}):
            assert is_configured() is False

    def test_is_configured_returns_true_when_complete(self):
        with patch(
            "server.sms._load_settings",
            return_value={
                "account_sid": "AC123",
                "auth_token": "tok",
                "from_number": "+1555",
            },
        ):
            assert is_configured() is True

    def test_update_settings_preserves_token_when_not_given(self, tmp_path):
        existing = tmp_path / "existing.json"
        existing.write_text(
            json.dumps({"account_sid": "AC123", "auth_token": "oldtok", "from_number": "+1555"})
        )
        with patch("server.sms.SETTINGS_PATH", existing):
            update_settings({"account_sid": "AC456"})
            saved = json.loads(existing.read_text())
            assert saved["account_sid"] == "AC456"
            assert saved["auth_token"] == "oldtok"

    def test_update_settings_updates_token(self, tmp_path):
        output = tmp_path / "out.json"
        output.write_text(json.dumps({"account_sid": "AC123"}))
        with patch("server.sms.SETTINGS_PATH", output):
            update_settings({"account_sid": "AC456", "auth_token": "newtok"})
            saved = json.loads(output.read_text())
            assert saved["auth_token"] == "newtok"

    def test_customer_phone_returns_none_for_no_customer(self):
        assert _customer_phone(None) is None

    def test_customer_phone_returns_mobile(self):
        assert _customer_phone({"mobile": "555-1111", "phone": "555-2222"}) == "555-1111"
        assert _customer_phone({"phone": "555-2222"}) == "555-2222"

    def test_customer_phone_returns_none_for_no_phone(self):
        assert _customer_phone({}) is None

    @pytest.mark.asyncio
    async def test_send_sms_returns_false_no_settings(self):
        with patch("server.sms._load_settings", return_value=None):
            result = await send_sms("+15551234567", "Hello")
            assert result is False

    @pytest.mark.asyncio
    async def test_send_sms_returns_false_incomplete_settings(self):
        with patch("server.sms._load_settings", return_value={"account_sid": "AC123"}):
            result = await send_sms("+15551234567", "Hello")
            assert result is False

    @pytest.mark.asyncio
    async def test_send_sms_normalizes_phone(self):
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post.return_value = mock_resp

        with patch(
            "server.sms._load_settings",
            return_value={
                "account_sid": "AC123",
                "auth_token": "tok",
                "from_number": "+15551234567",
            },
        ):
            with patch("server.sms.get_http_client", return_value=mock_client):
                result = await send_sms("5551234567", "Hello")
                assert result is True

    @pytest.mark.asyncio
    async def test_send_sms_failure(self):
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Error"
        mock_resp.json.return_value = {"message": "Invalid number"}
        mock_client.post.return_value = mock_resp

        with patch(
            "server.sms._load_settings",
            return_value={
                "account_sid": "AC123",
                "auth_token": "tok",
                "from_number": "+15551234567",
            },
        ):
            with patch("server.sms.get_http_client", return_value=mock_client):
                result = await send_sms("+15551234567", "Hello")
                assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_no_settings(self):
        with patch("server.sms._load_settings", return_value=None):
            result = await _sms_test_connection()
            assert result["ok"] is False

    def test_notify_ticket_status_change_calls_send(self):
        with patch("asyncio.ensure_future") as mock_ensure:
            _notify_ticket_status_change("+15551234567", 123, "Fix pc", "new")
            mock_ensure.assert_called_once()

    def test_notify_invoice_created_calls_send(self):
        with patch("asyncio.ensure_future") as mock_ensure:
            _notify_invoice_created("+15551234567", 456, 150.00)
            mock_ensure.assert_called_once()

    def test_notify_payment_received_calls_send(self):
        with patch("asyncio.ensure_future") as mock_ensure:
            _notify_payment_received("+15551234567", 456, 100.00)
            mock_ensure.assert_called_once()

    def test_notify_appointment_created_calls_send(self):
        with patch("asyncio.ensure_future") as mock_ensure:
            _notify_appointment_created("+15551234567", "Repair", 1700000000000)
            mock_ensure.assert_called_once()

    def test_notify_estimate_approved_calls_send(self):
        with patch("asyncio.ensure_future") as mock_ensure:
            _notify_estimate_approved("+15551234567", 789, 250.00)
            mock_ensure.assert_called_once()

    def test_notify_appointment_reminder_calls_send(self):
        with patch("asyncio.ensure_future") as mock_ensure:
            _notify_appointment_reminder("+15551234567", "Checkup", 1700000000000)
            mock_ensure.assert_called_once()

    def test_notify_overdue_reminder_calls_send(self):
        with patch("asyncio.ensure_future") as mock_ensure:
            _notify_overdue_reminder("+15551234567", 456, 200.00)
            mock_ensure.assert_called_once()
