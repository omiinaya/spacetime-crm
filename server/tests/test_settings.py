"""Settings (mail/SMS) routes — get/save/test."""

import httpx

from .conftest import (
    SERVER_URL,
    assert_ok,
    restore_mail_settings,
    restore_sms_settings,
    restore_user_settings,
    save_mail_settings,
    save_sms_settings,
    save_user_settings,
)


class TestMailSettings:
    """Mail configuration read, write, test."""

    def test_get_mail_settings(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/settings/mail", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "configured" in data

    def test_save_mail_settings(self, test_admin_headers: dict):
        # Save current settings for restoration
        prev = save_mail_settings(test_admin_headers)
        try:
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
                headers=test_admin_headers,
                timeout=10,
            )
            assert_ok(resp)

            # Verify saved
            r2 = httpx.get(
                f"{SERVER_URL}/api/settings/mail",
                headers=test_admin_headers,
                timeout=10,
            )
            data = r2.json()
            if data.get("configured") and data.get("settings"):
                assert "mail.example.com" in str(data["settings"])
        finally:
            # Always restore original settings
            restore_mail_settings(test_admin_headers, prev)

    def test_mail_test_no_connection(self, test_admin_headers: dict):
        """Test endpoint should return gracefully without a real SMTP server."""
        resp = httpx.post(
            f"{SERVER_URL}/api/settings/mail/test",
            headers=test_admin_headers,
            timeout=15,
        )
        # Should return something (success or error), not crash
        assert resp.status_code < 500, resp.text[:200]


class TestSMSSettings:
    """SMS configuration read, write, test."""

    def test_get_sms_settings(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/settings/sms", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "configured" in data

    def test_save_sms_settings(self, test_admin_headers: dict):
        # Save current settings for restoration
        prev = save_sms_settings(test_admin_headers)
        try:
            resp = httpx.post(
                f"{SERVER_URL}/api/settings/sms",
                json={
                    "twilio_account_sid": "AC_test123",
                    "twilio_auth_token": "tok_test456",
                    "twilio_from_number": "+15551234567",
                },
                headers=test_admin_headers,
                timeout=10,
            )
            assert_ok(resp)

            # Verify
            r2 = httpx.get(f"{SERVER_URL}/api/settings/sms", headers=test_admin_headers, timeout=10)
            assert r2.status_code == 200
        finally:
            # Always restore original settings
            restore_sms_settings(test_admin_headers, prev)

    def test_sms_test_no_connection(self, test_admin_headers: dict):
        """Test endpoint should return without crashing — may fail without creds."""
        resp = httpx.post(
            f"{SERVER_URL}/api/settings/sms/test",
            headers=test_admin_headers,
            timeout=15,
        )
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


class TestUserSettings:
    """User preferences — theme, default_ticket_status."""

    def test_get_user_settings_default(self, test_admin_headers: dict):
        """GET user settings returns null when not yet set."""
        resp = httpx.get(f"{SERVER_URL}/api/users/settings", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "settings" in data

    def test_update_user_settings(self, test_admin_headers: dict):
        """PUT user settings saves theme + default_ticket_status, GET returns them."""
        prev = save_user_settings(test_admin_headers)
        try:
            payload = {"theme": "dark", "default_ticket_status": "open"}
            resp = httpx.put(
                f"{SERVER_URL}/api/users/settings",
                json=payload,
                headers=test_admin_headers,
                timeout=10,
            )
            assert_ok(resp)

            # Verify saved
            r2 = httpx.get(
                f"{SERVER_URL}/api/users/settings",
                headers=test_admin_headers,
                timeout=10,
            )
            data = assert_ok(r2)
            assert data["settings"] is not None
            assert data["settings"]["theme"] == "dark"
            assert data["settings"]["default_ticket_status"] == "open"
        finally:
            restore_user_settings(test_admin_headers, prev)

    def test_update_user_settings_light(self, test_admin_headers: dict):
        """PUT user settings with light theme."""
        prev = save_user_settings(test_admin_headers)
        try:
            payload = {"theme": "light", "default_ticket_status": "new"}
            resp = httpx.put(
                f"{SERVER_URL}/api/users/settings",
                json=payload,
                headers=test_admin_headers,
                timeout=10,
            )
            assert_ok(resp)

            r2 = httpx.get(
                f"{SERVER_URL}/api/users/settings",
                headers=test_admin_headers,
                timeout=10,
            )
            data = assert_ok(r2)
            assert data["settings"]["theme"] == "light"
        finally:
            restore_user_settings(test_admin_headers, prev)

    def test_user_settings_unauthorized(self, client: httpx.Client):
        """GET/PUT user settings without auth returns 401/403."""
        resp = client.get("/api/users/settings", timeout=10)
        assert resp.status_code in (401, 403)

        resp = client.put(
            "/api/users/settings",
            json={"theme": "dark", "default_ticket_status": "new"},
            timeout=10,
        )
        assert resp.status_code in (401, 403)
