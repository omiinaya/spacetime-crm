"""Unit tests for auth routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt
    from config import settings
    token = jwt.encode({"sub": "user-1", "id": "user-1", "email": "admin@crm.local", "name": "Admin", "tenant_id": "t1", "role": "admin"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    def test_auth_me_unauthorized(self, client) -> None:
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_auth_me(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True, "totp_enabled": False, "pin": ""}],
            [],
        ])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        resp = client.get("/api/auth/me", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "user-1"
        assert data["email"] == "admin@crm.local"

    def test_set_password_success(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True}])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.auth._call", mock_call)
        body = {"password": "newpass123456"}
        resp = client.post("/api/auth/set-password", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_set_password_too_short(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True}])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        monkeypatch.setattr("routes.auth._call", AsyncMock())
        body = {"password": "short"}
        resp = client.post("/api/auth/set-password", json=body, headers=admin_headers())
        assert resp.status_code == 400

    def test_set_pin(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True}])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.auth._call", mock_call)
        body = {"pin": "1234"}
        resp = client.post("/api/auth/set-pin", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_set_pin_empty(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True}])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.auth._call", mock_call)
        body = {"pin": ""}
        resp = client.post("/api/auth/set-pin", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_set_pin_too_short(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True}])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        monkeypatch.setattr("routes.auth._call", AsyncMock())
        body = {"pin": "12"}
        resp = client.post("/api/auth/set-pin", json=body, headers=admin_headers())
        assert resp.status_code == 400

    def test_disable_2fa(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True}],
            [{"id": "user-1", "totp_secret": "JBSWY3DPEHPK3PXP"}],
        ])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        monkeypatch.setattr("routes.auth._call", AsyncMock())
        monkeypatch.setattr("routes.auth.pyotp.TOTP", lambda secret: type("obj", (), {"verify": lambda self, code, valid_window=0: True})())
        body = {"code": "123456"}
        resp = client.post("/api/auth/disable-2fa", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_refresh_tenant(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True}],
        ])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.auth._call", mock_call)
        resp = client.post("/api/auth/refresh-tenant", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data

    def test_setup_2fa(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "user-1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "active": True, "totp_enabled": False}],
            [],
        ])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.auth._call", mock_call)
        monkeypatch.setattr("routes.auth.pyotp.random_base32", lambda: "JBSWY3DPEHPK3PXP")
        class FakeTOTP:
            def __init__(self, secret):
                self.secret = secret
            def provisioning_uri(self, name, issuer_name):
                return f"otpauth://totp/{issuer_name}:{name}?secret={self.secret}"
        monkeypatch.setattr("routes.auth.pyotp.totp.TOTP", lambda secret: FakeTOTP(secret))
        resp = client.post("/api/auth/setup-2fa", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "secret" in data
        assert "provisioning_uri" in data

    def test_pos_login(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "u1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "pin": "hashed_pin", "active": True}],
            [],
        ])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        monkeypatch.setattr("routes.auth._sanitize_sql", lambda x: x)
        monkeypatch.setattr("routes.auth.bcrypt.checkpw", lambda pw, hashed: True)
        body = {"user_id": "u1", "pin": "1234"}
        resp = client.post("/api/auth/pos-login", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data

    def test_pos_login_invalid_pin(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "u1", "email": "admin@crm.local", "name": "Admin", "role": "admin", "pin": "hashed_pin", "active": True}])
        monkeypatch.setattr("routes.auth._sql", mock_sql)
        monkeypatch.setattr("routes.auth._sanitize_sql", lambda x: x)
        monkeypatch.setattr("routes.auth.bcrypt.checkpw", lambda pw, hashed: False)
        body = {"user_id": "u1", "pin": "9999"}
        resp = client.post("/api/auth/pos-login", json=body)
        assert resp.status_code == 401