"""Push notification engine — Web Push (VAPID) for browser notifications.

Requires:
    pip install pywebpush cryptography

VAPID keys are auto-generated on first use and stored in the backend's config.
Set VAPID_CLAIMS_EMAIL in .env to customize the contact email for push service.
"""

from __future__ import annotations

import asyncio
import json
import os

from helpers import _call, _sql, logger

# Optional: pywebpush for sending push notifications
try:
    from pywebpush import WebPushException, webpush

    HAS_PYWEBPUSH = True
except ImportError:
    HAS_PYWEBPUSH = False
    logger.warning(
        "pywebpush not installed — push notifications disabled. Install: pip install pywebpush cryptography"
    )
    webpush = None  # type: ignore
    WebPushException = type("WebPushException", (Exception,), {})  # type: ignore

# VAPID private key is stored in app config / env
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@spacetimecrm.local")
VAPID_CLAIMS = {"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"}

_PRIVATE_KEY: str | None = None


def _get_vapid_private_key() -> str | None:
    """Get or generate the VAPID private key for push notifications."""
    global _PRIVATE_KEY
    if _PRIVATE_KEY:
        return _PRIVATE_KEY
    # Try env var first
    key = os.environ.get("VAPID_PRIVATE_KEY")
    if key:
        _PRIVATE_KEY = key
        return key
    # Try file
    key_file = os.environ.get("VAPID_PRIVATE_KEY_FILE", "/app/server/vapid_private_key.pem")
    try:
        with open(key_file) as f:
            key = f.read().strip()
            _PRIVATE_KEY = key
            return key
    except (FileNotFoundError, PermissionError):
        pass
    # Generate a development key on first use
    if HAS_PYWEBPUSH:
        try:
            from pywebpush import generate_vapid_keys

            vapid_keys = generate_vapid_keys()
            _PRIVATE_KEY = vapid_keys["private_key"]
            # Save for reuse
            try:
                os.makedirs(os.path.dirname(key_file) or ".", exist_ok=True)
                with open(key_file, "w") as f:
                    f.write(vapid_keys["private_key"])
                logger.info("Generated new VAPID private key at %s", key_file)
            except OSError:
                pass
            return _PRIVATE_KEY  # type: ignore[return-value]
        except Exception as e:
            logger.warning("Failed to generate VAPID keys: %s", e)
    return None


async def get_user_subscriptions(user_id: str) -> list[dict]:
    """Fetch all push subscription endpoints for a user."""
    rows = await _sql(f"SELECT * FROM push_subscriptions WHERE user_id = '{user_id}'")
    return rows


async def subscribe(
    user_id: str,
    tenant_id: str,
    endpoint: str,
    p256dh_key: str,
    auth_key: str,
    user_agent: str = "",
):
    """Save a new push subscription."""
    await _call(
        "save_push_subscription", [user_id, tenant_id, endpoint, p256dh_key, auth_key, user_agent]
    )


async def unsubscribe(subscription_id: str):
    """Remove a subscription."""
    await _call("remove_push_subscription", [subscription_id])


async def send_notification_to_user(
    user_id: str,
    title: str,
    body: str,
    icon: str = "/favicon.ico",
    url: str = "",
) -> int:
    """Send a push notification to all devices of a user.

    Returns the number of successful deliveries.
    """
    if not HAS_PYWEBPUSH:
        logger.debug("Push skipped: pywebpush not installed")
        return 0
    private_key = _get_vapid_private_key()
    if not private_key:
        logger.debug("Push skipped: no VAPID private key")
        return 0

    subs = await get_user_subscriptions(user_id)
    if not subs:
        return 0

    payload = json.dumps({"title": title, "body": body, "icon": icon, "url": url})
    success = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh_key"], "auth": sub["auth_key"]},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=VAPID_CLAIMS,
            )
            success += 1
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                # Subscription expired — remove it
                logger.info("Removing expired push subscription %s", sub.get("id", "")[:12])
                asyncio.ensure_future(unsubscribe(sub["id"]))
            else:
                logger.warning("Push send failed for %s: %s", sub.get("id", "")[:12], e)
        except Exception as e:
            logger.warning("Push send error for %s: %s", sub.get("id", "")[:12], e)
    return success


async def send_notification_to_all_staff(
    title: str,
    body: str,
    icon: str = "/favicon.ico",
    url: str = "",
) -> int:
    """Send push notification to all admin/tech users across all tenants."""
    staff = await _sql(
        "SELECT id FROM \"user\" WHERE (role = 'admin' OR role = 'tech') AND active = true"
    )
    total = 0
    for s in staff:
        total += await send_notification_to_user(s["id"], title, body, icon, url)
    return total
