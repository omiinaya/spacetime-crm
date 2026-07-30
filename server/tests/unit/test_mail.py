"""Unit tests for server/mail.py.

Tests settings management, email sending logic, and notification
template rendering. SMTP connections are mocked.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _patch_path():
    """Replace SETTINGS_PATH with a temporary file for each test."""
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    import mail

    orig = mail.SETTINGS_PATH
    mail.SETTINGS_PATH = Path(p)
    yield
    mail.SETTINGS_PATH = orig
    if Path(p).exists():
        Path(p).unlink()


@pytest.fixture
def _full_settings() -> dict:
    """Return a complete, valid mail settings dict."""
    return {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user@example.com",
        "password": "secret",
        "use_tls": True,
        "sender_name": "Test CRM",
        "sender_email": "crm@example.com",
    }


class TestSettings:
    """Mail settings loading, saving, and updating."""

    def test_load_no_file(self) -> None:
        from mail import _load_settings

        assert _load_settings() is None

    def test_load_valid(self, _full_settings) -> None:
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))
        assert mail._load_settings() == _full_settings

    def test_load_parse_error(self) -> None:
        import mail

        mail.SETTINGS_PATH.write_text("invalid json")
        with patch("mail.logger"):
            result = mail._load_settings()
            assert result is None

    def test_save_settings(self) -> None:
        import mail

        mail._save_settings({"key": "value"})
        assert mail._load_settings() == {"key": "value"}

    def test_get_settings_without_password(self, _full_settings) -> None:
        """get_settings() should never return the password."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))
        result = mail.get_settings()
        assert result is not None
        assert "password" not in result
        assert result["host"] == "smtp.example.com"
        assert result["sender_email"] == "crm@example.com"

    def test_get_settings_no_file(self) -> None:
        from mail import get_settings

        assert get_settings() is None

    def test_get_settings_not_configured(self) -> None:
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps({"host": ""}))
        result = mail.get_settings()
        assert result is not None
        assert result["host"] == ""

    def test_update_settings_preserves_existing(self) -> None:
        import mail

        initial = {
            "host": "smtp.old.com",
            "port": 587,
            "username": "old@example.com",
            "password": "oldpass",
            "use_tls": True,
            "sender_name": "Old CRM",
            "sender_email": "old@example.com",
        }
        mail.SETTINGS_PATH.write_text(json.dumps(initial))
        mail.update_settings({"host": "smtp.new.com"})
        saved = json.loads(mail.SETTINGS_PATH.read_text())
        assert saved["host"] == "smtp.new.com"
        assert saved["username"] == "old@example.com"
        assert saved["password"] == "oldpass"

    def test_update_settings_adds_password(self) -> None:
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps({"host": "smtp.com", "port": 587}))
        mail.update_settings({"password": "newpassword"})
        saved = json.loads(mail.SETTINGS_PATH.read_text())
        assert saved["password"] == "newpassword"

    def test_update_settings_returns_public_view(self, _full_settings) -> None:
        """update_settings() should return the public view (no password)."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))
        result = mail.update_settings({"host": "smtp.updated.com"})
        assert "password" not in result
        assert result["host"] == "smtp.updated.com"


class TestSendEmail:
    """SMTP email sending logic."""

    def test_no_settings_returns_false(self) -> None:
        from mail import send_email

        result = send_email("to@test.com", "Subject", "<p>Body</p>")
        assert result is False

    def test_not_configured_empty_host(self) -> None:
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps({"host": "", "sender_email": ""}))
        result = mail.send_email("to@test.com", "Sub", "<p>Body</p>")
        assert result is False

    def test_not_configured_empty_sender(self) -> None:
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps({"host": "smtp.com", "sender_email": ""}))
        result = mail.send_email("to@test.com", "Sub", "<p>Body</p>")
        assert result is False

    def test_successful_send_with_tls(self, _full_settings) -> None:
        """Should successfully send via STARTTLS."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance

            result = mail.send_email("to@test.com", "Hello", "<html><body>Test</body></html>")

        assert result is True
        instance.ehlo.assert_called()
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("user@example.com", "secret")
        instance.send_message.assert_called_once()
        args, _ = instance.send_message.call_args
        msg = args[0]
        assert msg["From"] == "Test CRM <crm@example.com>"
        assert msg["To"] == "to@test.com"
        assert msg["Subject"] == "Hello"

    def test_successful_send_without_auth(self) -> None:
        """Should send without login if no username is set."""
        import mail

        settings = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "",
            "password": "",
            "use_tls": True,
            "sender_name": "Test",
            "sender_email": "test@example.com",
        }
        mail.SETTINGS_PATH.write_text(json.dumps(settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            result = mail.send_email("to@test.com", "Hello", "<p>Body</p>")

        assert result is True
        instance.login.assert_not_called()

    def test_successful_send_with_ssl(self) -> None:
        """Should send via SMTP_SSL when use_tls is False."""
        import mail

        settings = {
            "host": "smtp.example.com",
            "port": 465,
            "username": "user",
            "password": "pass",
            "use_tls": False,
            "sender_name": "Test",
            "sender_email": "test@example.com",
        }
        mail.SETTINGS_PATH.write_text(json.dumps(settings))

        with patch("mail.smtplib.SMTP_SSL") as mock_smtp_ssl:
            instance = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = instance
            result = mail.send_email("to@test.com", "Hello", "<p>Body</p>")

        assert result is True
        instance.login.assert_called_once_with("user", "pass")

    def test_failure_returns_false(self, _full_settings) -> None:
        """Should return False and log when SMTP raises an exception."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            instance.send_message.side_effect = ConnectionRefusedError("Connection refused")
            mock_smtp.return_value.__enter__.return_value = instance
            with patch("mail.logger") as mock_logger:
                result = mail.send_email("to@test.com", "Hello", "<p>Body</p>")

        assert result is False
        mock_logger.error.assert_called()

    def test_send_with_plain_text_fallback(self, _full_settings) -> None:
        """Should attach plain text fallback when provided."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            mail.send_email("to@test.com", "Hello", "<p>HTML</p>", text_body="Plain text")

        msg = instance.send_message.call_args[0][0]
        payload_types = [p.get_content_type() for p in msg.get_payload()]
        assert "text/plain" in payload_types
        assert "text/html" in payload_types

    def test_send_with_default_plain_text(self, _full_settings) -> None:
        """Should attach default plain text when not provided."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            mail.send_email("to@test.com", "Hello", "<p>HTML</p>")

        msg = instance.send_message.call_args[0][0]
        parts = msg.get_payload()
        assert any("HTML client" in str(p) for p in parts)

    def test_logs_success(self, _full_settings) -> None:
        """Should log when email is sent successfully."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            with patch("mail.logger") as mock_logger:
                mail.send_email("to@test.com", "Hello", "<p>Body</p>")

        mock_logger.info.assert_called_with("Email sent to %s: %s", "to@test.com", "Hello")


class TestConnection:
    """SMTP connection testing."""

    def test_no_settings(self) -> None:
        from mail import test_connection

        result = test_connection()
        assert result["ok"] is False
        assert "not configured" in result["error"].lower()

    def test_incomplete_settings(self) -> None:
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps({"host": "", "sender_email": ""}))
        result = mail.test_connection()
        assert result["ok"] is False

    def test_connection_tls_success(self, _full_settings) -> None:
        """Should return success when TLS connection works."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            result = mail.test_connection()

        assert result["ok"] is True
        assert "Connected" in result["message"]
        instance.ehlo.assert_called()
        instance.starttls.assert_called_once()

    def test_connection_ssl_success(self) -> None:
        """Should return success when SSL connection works."""
        import mail

        settings = {
            "host": "smtp.example.com",
            "port": 465,
            "username": "",
            "password": "",
            "use_tls": False,
            "sender_name": "Test",
            "sender_email": "test@example.com",
        }
        mail.SETTINGS_PATH.write_text(json.dumps(settings))

        with patch("mail.smtplib.SMTP_SSL") as mock_smtp_ssl:
            instance = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = instance
            result = mail.test_connection()

        assert result["ok"] is True
        instance.login.assert_not_called()

    def test_connection_failure(self, _full_settings) -> None:
        """Should return error when connection fails."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            instance.ehlo.side_effect = TimeoutError("Timed out")
            mock_smtp.return_value.__enter__.return_value = instance
            with patch("mail.logger"):
                result = mail.test_connection()

        assert result["ok"] is False
        assert "Timed out" in result["error"]

    def test_connection_with_auth(self, _full_settings) -> None:
        """Should log in when username is provided."""
        import mail

        mail.SETTINGS_PATH.write_text(json.dumps(_full_settings))

        with patch("mail.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            result = mail.test_connection()

        assert result["ok"] is True
        instance.login.assert_called_once_with("user@example.com", "secret")


class TestNotifications:
    """Email notification template rendering and dispatch."""

    def _check_notification(self, func_name: str, *args, **kwargs) -> None:
        """Verify a notification function calls send_email with the right args."""
        import mail

        with patch.object(mail, "send_email") as mock_send:
            getattr(mail, func_name)(*args, **kwargs)
            mock_send.assert_called_once()

    def test_ticket_status_change(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_ticket_status_change",
                "cust@test.com",
                101,
                "Screen broken",
                "in_progress",
                "http://link",
            )

    def test_invoice_created(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_invoice_created", "cust@test.com", 201, 150.0, "http://link"
            )

    def test_payment_received(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_payment_received", "cust@test.com", 201, 50.0, "http://link"
            )

    def test_appointment_created(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_appointment_created",
                "cust@test.com",
                "Repair",
                1710000000000,
                "http://link",
            )

    def test_estimate_approved(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_estimate_approved", "cust@test.com", 301, 250.0, "http://link"
            )

    def test_low_stock(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_low_stock",
                "admin@test.com",
                [
                    {
                        "name": "Widget",
                        "sku": "WGT",
                        "quantity_on_hand": 2,
                        "min_stock": 5,
                    }
                ],
            )

    def test_low_stock_empty_list(self) -> None:
        """Should not send email when products list is empty."""
        import mail

        with patch.object(mail, "send_email") as mock_send:
            mail._notify_low_stock("admin@test.com", [])
            mock_send.assert_not_called()

    def test_appointment_reminder(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_appointment_reminder",
                "cust@test.com",
                "Repair",
                1710000000000,
                "http://link",
            )

    def test_overdue_reminder(self) -> None:
        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            self._check_notification(
                "_notify_overdue_reminder",
                "cust@test.com",
                401,
                100.0,
                "2025-01-15",
                "http://link",
            )

    def test_customer_email(self) -> None:
        from mail import _customer_email

        assert _customer_email({"email": "a@b.com"}) == "a@b.com"
        assert _customer_email({"email": None}) is None
        assert _customer_email(None) is None
        assert _customer_email({}) is None

    def test_notification_templates_render(self) -> None:
        """Verify each notification template renders without error."""
        import mail

        with patch("mail.jinja_env") as mock_jinja:
            mock_template = MagicMock()
            mock_template.render.return_value = "<html>Rendered</html>"
            mock_jinja.get_template.return_value = mock_template

            with patch.object(mail, "send_email") as mock_send:
                mail._notify_ticket_status_change("a@b.com", 1, "Test", "new", "http://link")
                mock_jinja.get_template.assert_called_with("email/ticket_status.html")
                mock_send.assert_called_once()

    def test_notification_sends_correct_subject(self) -> None:
        """Notifications should have descriptive email subjects."""
        import mail

        with patch("mail.jinja_env") as mock_jinja:
            mock_jinja.get_template.return_value.render.return_value = "<html/>"
            with patch.object(mail, "send_email") as mock_send:
                mail._notify_ticket_status_change(
                    "a@b.com", 42, "Broken", "in_progress", "http://link"
                )
                subject = mock_send.call_args[0][1]
                assert "Ticket #42" in subject
                assert "In Progress" in subject

                mail._notify_invoice_created("a@b.com", 99, 199.99, "http://link")
                subject = mock_send.call_args[0][1]
                assert "Invoice #99" in subject
