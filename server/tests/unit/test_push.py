"""Unit tests for routes/push.py — Web Push (VAPID) subscription endpoints.

routes/push.py is the only route module with zero coverage. These tests
exercise all three endpoints (subscribe / unsubscribe / test-send) through
a TestClient with the auth dependency's ``_sql`` mocked and the push engine
functions patched out, plus engine-level tests for the send path's
"missing VAPID config" and delivery-counting behavior.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import types
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import main
import push
import pytest
from config import settings
from fastapi.testclient import TestClient

ADMIN_USER = {"id": "user_1", "role": "admin", "active": True, "email": "admin@test.local"}
TECH_USER = {"id": "user_2", "role": "tech", "active": True, "email": "tech@test.local"}

VALID_SUB = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc123",
    "p256dh_key": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
    "auth_key": "PTk6zVlq1Hp2YfZ8",
    "user_agent": "pytest-browser/1.0",
}


def _token(user: dict, tenant_id: str = "tenant_1") -> str:
    """Build a valid HS256 JWT for the given user dict."""
    return jwt.encode(
        {"sub": user["id"], "tenant_id": tenant_id, "role": user["role"]},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _headers(user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


_USER_ROWS = {u["id"]: u for u in (ADMIN_USER, TECH_USER)}


async def _fake_sql(query: str) -> list[dict]:
    """Stand-in for helpers._sql: return the row for the user in the query."""
    match = re.search(r"id = '([^']+)'", query)
    return [_USER_ROWS[match.group(1)]] if match else []


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient with the auth dependency's STDB lookup stubbed out."""
    with patch("helpers._sql", new=_fake_sql):
        yield TestClient(main.app)


class TestSubscribeRoute:
    """POST /api/push/subscribe."""

    @pytest.mark.parametrize(
        "missing",
        [
            {"endpoint", "p256dh_key", "auth_key"},
            {"p256dh_key", "auth_key"},
            {"endpoint", "auth_key"},
            {"endpoint", "p256dh_key"},
        ],
    )
    def test_missing_fields_rejected(self, client: TestClient, missing: set[str]) -> None:
        body = {k: v for k, v in VALID_SUB.items() if k not in missing}
        resp = client.post("/api/push/subscribe", json=body, headers=_headers(ADMIN_USER))
        assert resp.status_code == 400
        assert "Missing required push subscription fields" in resp.json()["detail"]

    def test_blank_fields_rejected(self, client: TestClient) -> None:
        """Whitespace-only values are treated as missing after .strip()."""
        resp = client.post(
            "/api/push/subscribe",
            json={"endpoint": "  ", "p256dh_key": "k", "auth_key": "a"},
            headers=_headers(ADMIN_USER),
        )
        assert resp.status_code == 400

    def test_accepts_valid_subscription(self, client: TestClient) -> None:
        with patch("routes.push.subscribe", new_callable=AsyncMock) as mock_sub:
            resp = client.post("/api/push/subscribe", json=VALID_SUB, headers=_headers(ADMIN_USER))
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_sub.assert_awaited_once_with(
            "user_1",
            "tenant_1",
            VALID_SUB["endpoint"],
            VALID_SUB["p256dh_key"],
            VALID_SUB["auth_key"],
            VALID_SUB["user_agent"],
        )

    def test_user_agent_defaults_to_empty(self, client: TestClient) -> None:
        body = {k: v for k, v in VALID_SUB.items() if k != "user_agent"}
        with patch("routes.push.subscribe", new_callable=AsyncMock) as mock_sub:
            resp = client.post("/api/push/subscribe", json=body, headers=_headers(ADMIN_USER))
        assert resp.status_code == 200
        args = mock_sub.await_args.args
        assert args[5] == ""

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/push/subscribe", json=VALID_SUB)
        assert resp.status_code == 401


class TestUnsubscribeRoute:
    """POST /api/push/unsubscribe."""

    def test_missing_subscription_id_rejected(self, client: TestClient) -> None:
        resp = client.post("/api/push/unsubscribe", json={}, headers=_headers(ADMIN_USER))
        assert resp.status_code == 400
        assert "Missing subscription_id" in resp.json()["detail"]

    def test_blank_subscription_id_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/push/unsubscribe",
            json={"subscription_id": "   "},
            headers=_headers(ADMIN_USER),
        )
        assert resp.status_code == 400

    def test_removes_subscription(self, client: TestClient) -> None:
        with patch("routes.push.unsubscribe", new_callable=AsyncMock) as mock_unsub:
            resp = client.post(
                "/api/push/unsubscribe",
                json={"subscription_id": "sub_123"},
                headers=_headers(ADMIN_USER),
            )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_unsub.assert_awaited_once_with("sub_123")

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/push/unsubscribe", json={"subscription_id": "sub_123"})
        assert resp.status_code == 401


class TestTestPushRoute:
    """POST /api/push/test — admin-only test notification."""

    def test_sends_test_notification(self, client: TestClient) -> None:
        with patch(
            "routes.push.send_notification_to_user", new_callable=AsyncMock, return_value=3
        ) as mock_send:
            resp = client.post("/api/push/test", headers=_headers(ADMIN_USER))
        assert resp.status_code == 200
        assert resp.json() == {"sent": 3}
        mock_send.assert_awaited_once_with(
            "user_1",
            "Test Notification",
            "Your push notifications are working!",
            url="/",
        )

    def test_missing_vapid_config_returns_zero(self, client: TestClient) -> None:
        """No VAPID key / no pywebpush → engine reports 0 deliveries."""
        with patch("routes.push.send_notification_to_user", new_callable=AsyncMock, return_value=0):
            resp = client.post("/api/push/test", headers=_headers(ADMIN_USER))
        assert resp.status_code == 200
        assert resp.json() == {"sent": 0}

    def test_requires_admin_role(self, client: TestClient) -> None:
        """tech/front_desk are allowed to subscribe/unsubscribe but not test-send."""
        resp = client.post("/api/push/test", headers=_headers(TECH_USER))
        assert resp.status_code == 403

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/push/test")
        assert resp.status_code == 401


class TestSendNotificationEngine:
    """push.send_notification_to_user — delivery counting & no-config paths."""

    async def test_missing_pywebpush_returns_zero(self) -> None:
        with patch.object(push, "HAS_PYWEBPUSH", False):
            count = await push.send_notification_to_user("user_1", "T", "B")
        assert count == 0

    async def test_missing_vapid_key_returns_zero(self) -> None:
        """No VAPID private key configured → nothing sent, returns 0."""
        with (
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.object(push, "_get_vapid_private_key", return_value=None),
            patch.object(push, "get_user_subscriptions", new_callable=AsyncMock) as mock_subs,
        ):
            count = await push.send_notification_to_user("user_1", "T", "B")
        assert count == 0
        mock_subs.assert_not_awaited()

    async def test_no_subscriptions_returns_zero(self) -> None:
        with (
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.object(push, "_get_vapid_private_key", return_value="priv"),
            patch.object(push, "get_user_subscriptions", new_callable=AsyncMock, return_value=[]),
        ):
            count = await push.send_notification_to_user("user_1", "T", "B")
        assert count == 0

    def _sub(self, sub_id: str) -> dict:
        return {
            "id": sub_id,
            "endpoint": f"https://push.example/{sub_id}",
            "p256dh_key": "p256dh",
            "auth_key": "auth",
        }

    async def test_sends_to_each_subscription(self) -> None:
        subs = [self._sub("sub_1"), self._sub("sub_2")]
        with (
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.object(push, "_get_vapid_private_key", return_value="priv"),
            patch.object(push, "get_user_subscriptions", new_callable=AsyncMock, return_value=subs),
            patch.object(push, "webpush", new=MagicMock()) as mock_webpush,
        ):
            count = await push.send_notification_to_user("user_1", "T", "B", url="/x")
        assert count == 2
        assert mock_webpush.call_count == 2
        for call in mock_webpush.call_args_list:
            kwargs = call.kwargs
            assert kwargs["vapid_private_key"] == "priv"
            assert (
                kwargs["data"] == '{"title": "T", "body": "B", "icon": "/favicon.ico", "url": "/x"}'
            )

    async def test_expired_subscription_removed(self) -> None:
        """A 404/410 response from the push service triggers async cleanup."""
        subs = [self._sub("sub_gone")]
        exc = push.WebPushException("gone")
        exc.response = MagicMock(status_code=410)
        with (
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.object(push, "_get_vapid_private_key", return_value="priv"),
            patch.object(push, "get_user_subscriptions", new_callable=AsyncMock, return_value=subs),
            patch.object(push, "webpush", new=MagicMock(side_effect=exc)),
            patch.object(push, "unsubscribe", new_callable=AsyncMock) as mock_unsub,
        ):
            count = await push.send_notification_to_user("user_1", "T", "B")
            # Drain the event loop so the ensure_future'd cleanup runs.
            for _ in range(5):
                await asyncio.sleep(0)
        assert count == 0
        mock_unsub.assert_awaited_once_with("sub_gone")

    async def test_generic_send_error_does_not_abort(self) -> None:
        """Non-WebPush errors are logged and the loop continues."""
        subs = [self._sub("sub_1"), self._sub("sub_2")]
        with (
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.object(push, "_get_vapid_private_key", return_value="priv"),
            patch.object(push, "get_user_subscriptions", new_callable=AsyncMock, return_value=subs),
            patch.object(push, "webpush", new=MagicMock(side_effect=[RuntimeError("boom"), None])),
        ):
            count = await push.send_notification_to_user("user_1", "T", "B")
        assert count == 1

    async def test_push_service_error_keeps_subscription(self) -> None:
        """A non-404/410 WebPushException (e.g. 500) logs a warning, keeps the sub."""
        subs = [self._sub("sub_keep")]
        exc = push.WebPushException("server error")
        exc.response = MagicMock(status_code=500)
        with (
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.object(push, "_get_vapid_private_key", return_value="priv"),
            patch.object(push, "get_user_subscriptions", new_callable=AsyncMock, return_value=subs),
            patch.object(push, "webpush", new=MagicMock(side_effect=exc)),
            patch.object(push, "unsubscribe", new_callable=AsyncMock) as mock_unsub,
        ):
            count = await push.send_notification_to_user("user_1", "T", "B")
            for _ in range(5):
                await asyncio.sleep(0)
        assert count == 0
        mock_unsub.assert_not_awaited()


class TestVapidKeyResolution:
    """push._get_vapid_private_key — env var, file, and generation sources."""

    def test_uses_env_var_key(self) -> None:
        with (
            patch.object(push, "_PRIVATE_KEY", None),
            patch.dict(os.environ, {"VAPID_PRIVATE_KEY": "env-key", "VAPID_PRIVATE_KEY_FILE": ""}),
        ):
            assert push._get_vapid_private_key() == "env-key"

    def test_reads_key_from_file(self, tmp_path) -> None:
        key_file = tmp_path / "vapid_private_key.pem"
        key_file.write_text("file-key\n")
        with (
            patch.object(push, "_PRIVATE_KEY", None),
            patch.dict(
                os.environ,
                {"VAPID_PRIVATE_KEY": "", "VAPID_PRIVATE_KEY_FILE": str(key_file)},
            ),
        ):
            assert push._get_vapid_private_key() == "file-key"

    def test_caches_key_across_calls(self) -> None:
        with (
            patch.object(push, "_PRIVATE_KEY", "cached-key"),
            patch.dict(os.environ, {"VAPID_PRIVATE_KEY": ""}),
        ):
            assert push._get_vapid_private_key() == "cached-key"

    def test_generates_and_saves_key(self, tmp_path) -> None:
        key_file = tmp_path / "generated.pem"
        fake_pywebpush = types.ModuleType("pywebpush")
        fake_pywebpush.generate_vapid_keys = lambda: {"private_key": "gen-key"}
        with (
            patch.object(push, "_PRIVATE_KEY", None),
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.dict(
                os.environ,
                {"VAPID_PRIVATE_KEY": "", "VAPID_PRIVATE_KEY_FILE": str(key_file)},
            ),
            patch.dict(sys.modules, {"pywebpush": fake_pywebpush}),
        ):
            assert push._get_vapid_private_key() == "gen-key"
        assert key_file.read_text().strip() == "gen-key"

    def test_generation_failure_returns_none(self, tmp_path) -> None:
        """Key generation raising → warn and return None (push stays disabled)."""
        key_file = tmp_path / "will-not-be-written.pem"
        fake_pywebpush = types.ModuleType("pywebpush")

        def _boom() -> None:
            raise RuntimeError("no keys today")

        fake_pywebpush.generate_vapid_keys = _boom
        with (
            patch.object(push, "_PRIVATE_KEY", None),
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.dict(
                os.environ,
                {"VAPID_PRIVATE_KEY": "", "VAPID_PRIVATE_KEY_FILE": str(key_file)},
            ),
            patch.dict(sys.modules, {"pywebpush": fake_pywebpush}),
        ):
            assert push._get_vapid_private_key() is None
        assert not key_file.exists()

    def test_generated_key_returns_even_if_save_fails(self, tmp_path) -> None:
        """An OSError persisting the key is swallowed; the key is still returned."""
        key_file = tmp_path / "unwritable.pem"
        fake_pywebpush = types.ModuleType("pywebpush")
        fake_pywebpush.generate_vapid_keys = lambda: {"private_key": "gen-key"}
        with (
            patch.object(push, "_PRIVATE_KEY", None),
            patch.object(push, "HAS_PYWEBPUSH", True),
            patch.object(push.os, "makedirs", side_effect=OSError("read-only fs")),
            patch.dict(
                os.environ,
                {"VAPID_PRIVATE_KEY": "", "VAPID_PRIVATE_KEY_FILE": str(key_file)},
            ),
            patch.dict(sys.modules, {"pywebpush": fake_pywebpush}),
        ):
            assert push._get_vapid_private_key() == "gen-key"
        assert not key_file.exists()


class TestSubscriptionEngine:
    """push.subscribe / push.unsubscribe / push.get_user_subscriptions reducers."""

    async def test_subscribe_calls_save_reducer(self) -> None:
        with patch.object(push, "_call", new_callable=AsyncMock) as mock_call:
            await push.subscribe("user_1", "tenant_1", "https://e", "pk", "ak", "UA")
        mock_call.assert_awaited_once_with(
            "save_push_subscription", ["user_1", "tenant_1", "https://e", "pk", "ak", "UA"]
        )

    async def test_unsubscribe_calls_remove_reducer(self) -> None:
        with patch.object(push, "_call", new_callable=AsyncMock) as mock_call:
            await push.unsubscribe("sub_123")
        mock_call.assert_awaited_once_with("remove_push_subscription", ["sub_123"])

    async def test_get_user_subscriptions_builds_query(self) -> None:
        with patch.object(
            push, "_sql", new_callable=AsyncMock, return_value=[{"id": "sub_1"}]
        ) as mock_sql:
            rows = await push.get_user_subscriptions("user_1")
        assert rows == [{"id": "sub_1"}]
        query = mock_sql.await_args.args[0]
        assert "push_subscriptions" in query
        assert "user_id = 'user_1'" in query


class TestSendToAllStaffEngine:
    """push.send_notification_to_all_staff — aggregates across staff users."""

    async def test_sums_deliveries_across_staff(self) -> None:
        staff = [{"id": "user_1"}, {"id": "user_2"}]
        with (
            patch.object(push, "_sql", new_callable=AsyncMock, return_value=staff),
            patch.object(
                push,
                "send_notification_to_user",
                new_callable=AsyncMock,
                side_effect=[2, 3],
            ),
        ):
            total = await push.send_notification_to_all_staff("T", "B", url="/")
        assert total == 5

    async def test_returns_zero_when_no_staff(self) -> None:
        with (
            patch.object(push, "_sql", new_callable=AsyncMock, return_value=[]),
            patch.object(push, "send_notification_to_user", new_callable=AsyncMock),
        ):
            total = await push.send_notification_to_all_staff("T", "B")
        assert total == 0
