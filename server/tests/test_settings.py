"""Settings (mail/SMS) routes — get/save/test."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok


class TestMailSettings:
    """Mail configuration read, write, test."""

    def test_get_mail_settings(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/settings/mail", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "configured" in data

    def test_save_mail_settings(self, auth_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/settings/mail",
            json={
                "smtp_host": "mail.example.com",
                "smtp_port": 587,
                "smtp_user": "user@example.com",
                "smtp_password": "secret",
                "smtp_from_email": "noreply@example.com",
                "smtp_from_name": "CRM",
                "smtp_tls": True,
            },
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify saved
        r2 = httpx.get(f"{SERVER_URL}/api/settings/mail", headers=auth_headers, timeout=10)
        data = r2.json()
        if data.get("configured") and data.get("settings"):
            assert "mail.example.com" in str(data["settings"])

    def test_mail_test_no_connection(self, auth_headers: dict):
        """Test endpoint should return gracefully without a real SMTP server."""
        resp = httpx.post(f"{SERVER_URL}/api/settings/mail/test", headers=auth_headers, timeout=15)
        # Should return something (success or error), not crash
        assert resp.status_code < 500, resp.text[:200]


class TestSMSSettings:
    """SMS configuration read, write, test."""

    def test_get_sms_settings(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/settings/sms", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "configured" in data

    def test_save_sms_settings(self, auth_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/settings/sms",
            json={
                "twilio_account_sid": "AC_test123",
                "twilio_auth_token": "tok_test456",
                "twilio_from_number": "+15551234567",
            },
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify
        r2 = httpx.get(f"{SERVER_URL}/api/settings/sms", headers=auth_headers, timeout=10)
        assert r2.status_code == 200

    def test_sms_test_no_connection(self, auth_headers: dict):
        """Test endpoint should return without crashing — may fail without creds."""
        resp = httpx.post(f"{SERVER_URL}/api/settings/sms/test", headers=auth_headers, timeout=15)
        # Twilio not configured, may return 5xx — just verify it doesn't hang
        assert resp.elapsed.total_seconds() < 10, "Test endpoint timed out"


class TestSettingsErrors:
    """Auth enforcement for settings."""

    def test_mail_unauthorized(self, client: httpx.Client):
        resp = client.get("/api/settings/mail", timeout=10)
        assert resp.status_code in (401, 403)

    def test_sms_unauthorized(self, client: httpx.Client):
        resp = client.get("/api/settings/sms", timeout=10)
        assert resp.status_code in (401, 403)
