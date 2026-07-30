"""Push notification subscription routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from helpers import require_role
from push import send_notification_to_user, subscribe, unsubscribe

router = APIRouter()


@router.post("/api/push/subscribe")
async def subscribe_push(
    body: dict, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Register a browser push subscription for push notifications."""
    endpoint = body.get("endpoint", "").strip()
    p256dh = body.get("p256dh_key", "").strip()
    auth = body.get("auth_key", "").strip()
    user_agent = body.get("user_agent", "")
    if not endpoint or not p256dh or not auth:
        raise HTTPException(400, "Missing required push subscription fields")

    await subscribe(
        user["id"],
        user.get("tenant_id", ""),
        endpoint,
        p256dh,
        auth,
        user_agent,
    )
    return {"ok": True}


@router.post("/api/push/unsubscribe")
async def unsubscribe_push(
    body: dict, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Remove a push subscription."""
    sub_id = body.get("subscription_id", "").strip()
    if not sub_id:
        raise HTTPException(400, "Missing subscription_id")
    await unsubscribe(sub_id)
    return {"ok": True}


@router.post("/api/push/test")
async def test_push(user: dict = Depends(require_role("admin"))):
    """Send a test push notification to the current user."""
    count = await send_notification_to_user(
        user["id"],
        "Test Notification",
        "Your push notifications are working!",
        url="/",
    )
    return {"sent": count}
