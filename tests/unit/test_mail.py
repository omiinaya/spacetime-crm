"""Tests for mail module (SMTP email sending with JSON settings)."""

import json
from unittest.mock import patch, mock_open


from mail import (
    _load_settings, _save_settings, get_settings, update_settings,
    send_email,
    _customer_email, _notify_ticket_status_change,
    _notify_invoice_created, _notify_appointment_created,
    _notify_payment_received, _notify_estimate_approved,
    _notify_low_stock, _notify_appointment_reminder, _notify_overdue_reminder,
)


class TestLoadSettings:
    def test_returns_none_when_file_missing(self):
        with patch("pathlib.Path.exists", return_value=False):
            assert _load_settings() is None

    def test_returns_parsed_json_when_file_exists(self):
        data = {"host": "smtp.example.com", "port": 587}
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(data))):
                assert _load_settings() == data

    def test_returns_none_on_corrupt_json(self):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="not json")):
                assert _load_settings() is None


class TestSaveSettings:
    def test_writes_to_file(self):
        data = {"host": "smtp.example.com"}
        with patch("pathlib.Path.write_text") as mock_write:
            _save_settings(data)
            written = json.loads(mock_write.call_args[0][0])
            assert written["host"] == "smtp.example.com"

    def test_logs_on_save(self):
        with patch("pathlib.Path.write_text"):
            with patch("mail.logger.info") as mock_log:
                _save_settings({"host": "x"})
                mock_log.assert_called_once()


class TestGetSettings:
    def test_returns_none_when_no_settings(self):
        with patch("mail._load_settings", return_value=None):
            assert get_settings() is None

    def test_strips_password(self):
        with patch("mail._load_settings", return_value={
            "host": "smtp.example.com", "port": 587, "password": "s3kr3t",
            "username": "user", "sender_email": "a@b.com",
        }):
            result = get_settings()
            assert "password" not in result
            assert result["host"] == "smtp.example.com"
            assert result["username"] == "user"

    def test_returns_safe_fields_only(self):
        with patch("mail._load_settings", return_value={"host": "h", "port": 25}):
            result = get_settings()
            assert set(result.keys()) == {"host", "port", "username", "use_tls", "sender_name", "sender_email"}


class TestUpdateSettings:
    def test_merges_with_existing(self):
        with patch("mail._load_settings", return_value={"host": "old.com", "port": 587}):
            with patch("mail._save_settings") as mock_save:
                update_settings({"host": "new.com"})
                # _save_settings is called before get_settings which returns safe
                args = mock_save.call_args[0][0]
                assert args["host"] == "new.com"
                assert args["port"] == 587

    def test_preserves_password_when_not_in_update(self):
        with patch("mail._load_settings", return_value={"password": "oldpass", "host": "h"}):
            with patch("mail._save_settings") as mock_save:
                update_settings({"host": "newh"})
                args = mock_save.call_args[0][0]
                assert args["password"] == "oldpass"

    def test_updates_password_when_provided(self):
        with patch("mail._load_settings", return_value={"password": "old"}):
            with patch("mail._save_settings") as mock_save:
                update_settings({"password": "new"})
                args = mock_save.call_args[0][0]
                assert args["password"] == "new"


class TestSendEmail:
    def test_returns_false_when_not_configured(self):
        with patch("mail._load_settings", return_value=None):
            assert send_email("a@b.com", "Subject", "<p>Body</p>") is False

    def test_returns_false_when_host_missing(self):
        with patch("mail._load_settings", return_value={"sender_email": "a@b.com"}):
            assert send_email("a@b.com", "Subject", "<p>Body</p>") is False

    def test_returns_false_when_sender_missing(self):
        with patch("mail._load_settings", return_value={"host": "smtp.example.com"}):
            assert send_email("a@b.com", "Subject", "<p>Body</p>") is False

    def test_sends_email_via_smtp_tls(self):
        settings = {
            "host": "smtp.example.com", "port": 587,
            "username": "user", "password": "pass",
            "sender_name": "CRM", "sender_email": "crm@ex.com",
            "use_tls": True,
        }
        with patch("mail._load_settings", return_value=settings):
            with patch("mail.smtplib.SMTP") as mock_smtp:
                instance = mock_smtp.return_value.__enter__.return_value
                result = send_email("to@ex.com", "Hello", "<p>World</p>")

        assert result is True
        instance.ehlo.assert_called()
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("user", "pass")
        instance.send_message.assert_called_once()

    def test_sends_email_via_smtp_ssl(self):
        settings = {
            "host": "smtp.example.com", "port": 465,
            "username": "user", "password": "pass",
            "sender_name": "CRM", "sender_email": "crm@ex.com",
            "use_tls": False,
        }
        with patch("mail._load_settings", return_value=settings):
            with patch("mail.smtplib.SMTP_SSL") as mock_smtp_ssl:
                instance = mock_smtp_ssl.return_value.__enter__.return_value
                result = send_email("to@ex.com", "Hello", "<p>World</p>")

        assert result is True
        instance.login.assert_called_once_with("user", "pass")
        instance.send_message.assert_called_once()

    def test_returns_false_on_smtp_error(self):
        settings = {"host": "bad.com", "port": 587, "sender_email": "a@b.com", "use_tls": True}
        with patch("mail._load_settings", return_value=settings):
            with patch("mail.smtplib.SMTP", side_effect=Exception("timeout")):
                result = send_email("to@ex.com", "Hello", "<p>World</p>")

        assert result is False


class TestTestConnection:
    def test_returns_ok_false_when_not_configured(self):
        from mail import test_connection
        with patch("mail._load_settings", return_value=None):
            result = test_connection()
            assert result == {"ok": False, "error": "Mail not configured"}

    def test_returns_ok_false_when_host_missing(self):
        from mail import test_connection
        with patch("mail._load_settings", return_value={"sender_email": "a@b.com"}):
            result = test_connection()
            assert result["ok"] is False

    def test_returns_ok_on_successful_connection(self):
        from mail import test_connection
        settings = {"host": "smtp.ex.com", "port": 587, "sender_email": "a@b.com", "use_tls": True}
        with patch("mail._load_settings", return_value=settings):
            with patch("mail.smtplib.SMTP") as mock_smtp:
                instance = mock_smtp.return_value.__enter__.return_value
                instance.ehlo_resp = "250 Ok"
                result = test_connection()
                assert result["ok"] is True


class TestCustomerEmail:
    def test_returns_email_when_present(self):
        assert _customer_email({"email": "a@b.com"}) == "a@b.com"

    def test_returns_none_when_no_customer(self):
        assert _customer_email(None) is None

    def test_returns_none_when_email_empty(self):
        assert _customer_email({"email": ""}) is None


class TestNotificationTemplates:
    def test_notify_ticket_status(self):
        with patch("mail._customer_email", return_value="a@b.com"):
            with patch("mail.send_email") as mock_send:
                with patch("mail.jinja_env.get_template") as mock_tpl:
                    mock_tpl.return_value.render.return_value = "<html/>"
                    _notify_ticket_status_change("a@b.com", 42, "Broken", "in_progress", "http://link")
                    mock_send.assert_called_once()
                    args, _ = mock_send.call_args
                    assert "Ticket #42" in args[1]

    def test_notify_invoice_created(self):
        with patch("mail.send_email") as mock_send:
            with patch("mail.jinja_env.get_template") as mock_tpl:
                mock_tpl.return_value.render.return_value = "<html/>"
                _notify_invoice_created("a@b.com", 101, 250.0, "http://link")
                mock_send.assert_called_once()
                args, _ = mock_send.call_args
                assert "Invoice #101" in args[1]

    def test_notify_appointment_created(self):
        with patch("mail.send_email") as mock_send:
            with patch("mail.jinja_env.get_template") as mock_tpl:
                mock_tpl.return_value.render.return_value = "<html/>"
                dt_ms = 1700000000000  # 2023-11-14
                _notify_appointment_created("a@b.com", "Screen Repair", dt_ms, "http://link")
                mock_send.assert_called_once()

    def test_notify_payment_received(self):
        with patch("mail.send_email") as mock_send:
            with patch("mail.jinja_env.get_template") as mock_tpl:
                mock_tpl.return_value.render.return_value = "<html/>"
                _notify_payment_received("a@b.com", 101, 100.0, "http://link")
                mock_send.assert_called_once()

    def test_notify_estimate_approved(self):
        with patch("mail.send_email") as mock_send:
            with patch("mail.jinja_env.get_template") as mock_tpl:
                mock_tpl.return_value.render.return_value = "<html/>"
                _notify_estimate_approved("a@b.com", 5, 500.0, "http://link")
                mock_send.assert_called_once()

    def test_notify_low_stock(self):
        with patch("mail.send_email") as mock_send:
            with patch("mail.jinja_env.get_template") as mock_tpl:
                mock_tpl.return_value.render.return_value = "<html/>"
                products = [{"name": "HDMI Cable", "sku": "HDMI-1", "quantity_on_hand": 2, "min_stock": 5}]
                _notify_low_stock("admin@ex.com", products)
                mock_send.assert_called_once()

    def test_notify_low_stock_empty_returns_early(self):
        with patch("mail.send_email") as mock_send:
            _notify_low_stock("admin@ex.com", [])
            mock_send.assert_not_called()

    def test_notify_appointment_reminder(self):
        with patch("mail.send_email") as mock_send:
            with patch("mail.jinja_env.get_template") as mock_tpl:
                mock_tpl.return_value.render.return_value = "<html/>"
                _notify_appointment_reminder("a@b.com", "Checkup", 1700000000000, "http://link")
                mock_send.assert_called_once()

    def test_notify_overdue_reminder(self):
        with patch("mail.send_email") as mock_send:
            with patch("mail.jinja_env.get_template") as mock_tpl:
                mock_tpl.return_value.render.return_value = "<html/>"
                _notify_overdue_reminder("a@b.com", 42, 150.0, "2024-01-15", "http://link")
                mock_send.assert_called_once()
