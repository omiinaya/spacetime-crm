"""Unit tests for settings routes."""


def admin_headers():
    import jwt

    from config import settings

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1", "role": "admin"}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


class TestSettings:
    def test_get_mail_settings(self, client, monkeypatch) -> None:
        monkeypatch.setattr("routes.settings._mail_get", lambda: {"smtp_host": "smtp.example.com", "enabled": False})
        resp = client.get("/api/settings/mail", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["settings"]["smtp_host"] == "smtp.example.com"

    def test_update_mail_settings(self, client, monkeypatch) -> None:
        monkeypatch.setattr("routes.settings._mail_update", lambda d: None)
        body = {
            "smtp_host": "smtp.new.com",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from_email": "",
            "smtp_from_name": "",
            "smtp_tls": True,
            "enabled": True,
        }
        resp = client.post("/api/settings/mail", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_test_mail(self, client, monkeypatch) -> None:
        monkeypatch.setattr("routes.settings._mail_test", lambda: {"status": "ok"})
        resp = client.post("/api/settings/mail/test", headers=admin_headers())
        assert resp.status_code == 200

    def test_get_sms_settings(self, client, monkeypatch) -> None:
        monkeypatch.setattr("routes.settings._sms_get", lambda: {"twilio_from_number": "+15551234567", "enabled": True})
        resp = client.get("/api/settings/sms", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["settings"]["twilio_from_number"] == "+15551234567"

    def test_update_sms_settings(self, client, monkeypatch) -> None:
        monkeypatch.setattr("routes.settings._sms_update", lambda d: None)
        body = {
            "twilio_account_sid": "sid",
            "twilio_auth_token": "tok",
            "twilio_from_number": "+1555",
            "enabled": False,
        }
        resp = client.post("/api/settings/sms", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_get_business_hours(self, client, monkeypatch) -> None:
        monkeypatch.setattr("routes.settings._bh_get", lambda **kw: {"monday": []})
        resp = client.get("/api/settings/business-hours", headers=admin_headers())
        assert resp.status_code == 200

    def test_update_business_hours(self, client, monkeypatch) -> None:
        monkeypatch.setattr("routes.settings._bh_update", lambda d: {})
        body = {"monday": {"open": "09:00", "close": "17:00"}}
        resp = client.post("/api/settings/business-hours", json=body, headers=admin_headers())
        assert resp.status_code == 200
