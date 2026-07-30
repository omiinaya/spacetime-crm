"""
Tests for server/mail.py.

Tests SMTP email configuration, sending, and notification templates.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from server.mail import (
    _customer_email,
    _load_settings,
    _notify_appointment_created,
    _notify_appointment_reminder,
    _notify_estimate_approved,
    _notify_invoice_created,
    _notify_low_stock,
    _notify_overdue_reminder,
    _notify_payment_received,
    _notify_ticket_status_change,
    _save_settings,
    get_settings,
    send_email,
    test_connection,
    update_settings,
)


class TestMail:
    """Test suite for mail.py."""

    def test_load_settings_no_file(self, tmp_path):
        """_load_settings returns None when file doesn't exist."""
        with patch("server.mail.SETTINGS_PATH", tmp_path / "nonexistent.json"):
            assert _load_settings() is None

    def test_load_settings_success(self, tmp_path):
        """_load_settings returns parsed JSON."""
        settings_file = tmp_path / "mail_settings.json"
        test_data = {"host": "smtp.example.com", "port": 587}
        settings_file.write_text(json.dumps(test_data))
        with patch("server.mail.SETTINGS_PATH", settings_file):
            result = _load_settings()
            assert result["host"] == "smtp.example.com"
            assert result["port"] == 587

    def test_load_settings_invalid_json(self, tmp_path):
        """_load_settings returns None on invalid JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        with patch("server.mail.SETTINGS_PATH", bad_file):
            assert _load_settings() is None

    def test_save_settings_writes(self, tmp_path):
        """_save_settings writes JSON to the settings path."""
        output = tmp_path / "out.json"
        with patch("server.mail.SETTINGS_PATH", output):
            _save_settings({"host": "test.com"})
            assert output.exists()
            saved = json.loads(output.read_text())
            assert saved["host"] == "test.com"

    def test_get_settings_strips_password(self):
        """get_settings never returns the password."""
        with patch(
            "server.mail._load_settings",
            return_value={
                "host": "smtp.com",
                "port": 587,
                "username": "u",
                "password": "secret",
            },
        ):
            result = get_settings()
            assert "password" not in result
            assert result["host"] == "smtp.com"

    def test_get_settings_no_settings(self):
        """get_settings returns None when no settings exist."""
        with patch("server.mail._load_settings", return_value=None):
            assert get_settings() is None

    def test_update_settings_preserves_password_when_not_given(self, tmp_path):
        """update_settings keeps existing password when not in new data."""
        existing = tmp_path / "existing.json"
        existing.write_text(json.dumps({"host": "old.com", "password": "oldpass"}))
        with patch("server.mail.SETTINGS_PATH", existing):
            update_settings({"host": "new.com"})
            saved = json.loads(existing.read_text())
            assert saved["host"] == "new.com"
            assert saved["password"] == "oldpass"

    def test_update_settings_updates_password(self, tmp_path):
        """update_settings sets password when provided."""
        output = tmp_path / "out.json"
        output.write_text(json.dumps({"host": "old.com"}))
        with patch("server.mail.SETTINGS_PATH", output):
            update_settings({"host": "new.com", "password": "newpass"})
            saved = json.loads(output.read_text())
            assert saved["password"] == "newpass"

    def test_update_settings_returns_safe_settings(self):
        """update_settings returns get_settings() result."""
        safe = {"host": "new.com", "port": 587}
        with patch("server.mail._load_settings", return_value={}):
            with patch("server.mail.get_settings", return_value=safe):
                result = update_settings({"host": "new.com"})
                assert result == safe

    def test_customer_email_returns_none_for_no_customer(self):
        """_customer_email returns None when customer is None."""
        assert _customer_email(None) is None

    def test_customer_email_returns_email(self):
        """_customer_email returns customer email."""
        assert _customer_email({"email": "a@b.com"}) == "a@b.com"

    def test_customer_email_returns_none_for_no_email(self):
        """_customer_email returns None when customer has no email."""
        assert _customer_email({}) is None

    def test_send_email_returns_false_no_settings(self):
        """send_email returns False when mail not configured."""
        with patch("server.mail._load_settings", return_value=None):
            assert send_email("a@b.com", "Subj", "<p>body</p>") is False

    def test_send_email_returns_false_incomplete_settings(self):
        """send_email returns False when host or sender missing."""
        with patch(
            "server.mail._load_settings", return_value={"host": "", "sender_email": ""}
        ):
            assert send_email("a@b.com", "Subj", "<p>body</p>") is False

    def test_test_connection_no_settings(self):
        """test_connection returns error when not configured."""
        with patch("server.mail._load_settings", return_value=None):
            result = test_connection()
            assert result["ok"] is False
            assert "not configured" in result["error"].lower()

    def test_notify_ticket_status_change_calls_send(self):
        """_notify_ticket_status_change calls send_email."""
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_ticket_status_change(
                    "a@b.com", 123, "Fix pc", "new", "http://link"
                )
                mock_send.assert_called_once()
                args = mock_send.call_args[0]
                assert args[0] == "a@b.com"

    def test_notify_invoice_created_calls_send(self):
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_invoice_created("a@b.com", 456, 150.00, "http://link")
                mock_send.assert_called_once()

    def test_notify_payment_received_calls_send(self):
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_payment_received("a@b.com", 456, 100.00, "http://link")
                mock_send.assert_called_once()

    def test_notify_appointment_created_calls_send(self):
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_appointment_created(
                    "a@b.com", "Repair", 1700000000000, "http://link"
                )
                mock_send.assert_called_once()

    def test_notify_estimate_approved_calls_send(self):
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_estimate_approved("a@b.com", 789, 250.00, "http://link")
                mock_send.assert_called_once()

    def test_notify_low_stock_no_products(self):
        with patch("server.mail.send_email") as mock_send:
            _notify_low_stock("a@b.com", [])
            mock_send.assert_not_called()

    def test_notify_low_stock_calls_send(self):
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_low_stock(
                    "a@b.com",
                    [
                        {
                            "name": "Widget",
                            "sku": "W1",
                            "quantity_on_hand": 1,
                            "min_stock": 5,
                        }
                    ],
                )
                mock_send.assert_called_once()

    def test_notify_appointment_reminder_calls_send(self):
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_appointment_reminder(
                    "a@b.com", "Checkup", 1700000000000, "http://link"
                )
                mock_send.assert_called_once()

    def test_notify_overdue_reminder_calls_send(self):
        with patch("server.mail.send_email") as mock_send:
            with patch("server.mail.jinja_env") as mock_env:
                mock_env.get_template.return_value.render.return_value = "<html/>"
                _notify_overdue_reminder(
                    "a@b.com", 456, 200.00, "2025-01-01", "http://link"
                )
                mock_send.assert_called_once()
