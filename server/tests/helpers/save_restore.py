"""Helpers for saving and restoring mutable settings during tests."""

from __future__ import annotations

import httpx

from tests.helpers.db import SERVER_URL


# ── Settings save/restore helpers ─────────────────────────────────


def save_mail_settings(auth_headers: dict) -> dict | None:
    """Fetch current mail settings so they can be restored later."""
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/settings/mail", headers=auth_headers, timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("settings")
    except Exception:
        pass
    return None


def restore_mail_settings(auth_headers: dict, settings: dict | None) -> None:
    """Restore previously saved mail settings."""
    if settings is None:
        return
    try:
        httpx.post(
            f"{SERVER_URL}/api/settings/mail",
            json={
                "smtp_host": settings.get("smtp_host", ""),
                "smtp_port": settings.get("smtp_port", 587),
                "smtp_user": settings.get("smtp_user", ""),
                "smtp_password": settings.get("smtp_password", ""),
                "smtp_from_email": settings.get("smtp_from_email", ""),
                "smtp_from_name": settings.get("smtp_from_name", ""),
                "smtp_tls": settings.get("smtp_tls", True),
            },
            headers=auth_headers,
            timeout=10,
        )
    except Exception:
        pass


def save_sms_settings(auth_headers: dict) -> dict | None:
    """Fetch current SMS settings so they can be restored later."""
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/settings/sms", headers=auth_headers, timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("settings")
    except Exception:
        pass
    return None


def restore_sms_settings(auth_headers: dict, settings: dict | None) -> None:
    """Restore previously saved SMS settings."""
    if settings is None:
        return
    try:
        httpx.post(
            f"{SERVER_URL}/api/settings/sms",
            json={
                "twilio_account_sid": settings.get("twilio_account_sid", ""),
                "twilio_auth_token": settings.get("twilio_auth_token", ""),
                "twilio_from_number": settings.get("twilio_from_number", ""),
            },
            headers=auth_headers,
            timeout=10,
        )
    except Exception:
        pass


def save_user_settings(auth_headers: dict) -> dict | None:
    """Fetch current user settings so they can be restored later."""
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/users/settings", headers=auth_headers, timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("settings")
    except Exception:
        pass
    return None


def restore_user_settings(auth_headers: dict, settings: dict | None) -> None:
    """Restore previously saved user settings."""
    if settings is None:
        return
    try:
        httpx.put(
            f"{SERVER_URL}/api/users/settings",
            json={
                "theme": settings.get("theme", "system"),
                "default_ticket_status": settings.get("default_ticket_status", "new"),
            },
            headers=auth_headers,
            timeout=10,
        )
    except Exception:
        pass


# ── SLA save/restore helpers ──────────────────────────────────────

DEFAULT_SLA_TARGETS = {"urgent": 4, "high": 24, "medium": 72, "low": 120}


def save_sla_targets(auth_headers: dict) -> dict:
    """Fetch current SLA targets and return them for later restoration."""
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/tickets/sla-settings",
            headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        return data.get("targets", dict(DEFAULT_SLA_TARGETS))
    except Exception:
        return dict(DEFAULT_SLA_TARGETS)


def restore_sla_targets(auth_headers: dict, targets: dict) -> None:
    """Restore SLA targets to previously saved values."""
    if not targets:
        targets = dict(DEFAULT_SLA_TARGETS)
    try:
        httpx.post(
            f"{SERVER_URL}/api/tickets/sla-settings",
            json={"targets": targets},
            headers=auth_headers,
            timeout=10,
        )
    except Exception:
        pass


def reset_sla_targets(auth_headers: dict) -> None:
    """Reset SLA targets back to defaults for test isolation."""
    restore_sla_targets(auth_headers, dict(DEFAULT_SLA_TARGETS))


# ── Default tax rate save/restore helpers ──────────────────────────


def save_default_tax_rate(auth_headers: dict) -> dict | None:
    """Fetch current default tax rate so it can be restored later."""
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/tax-rates", headers=auth_headers, timeout=10
        )
        if resp.status_code == 200:
            rates = resp.json().get("tax_rates", [])
            for rate in rates:
                if rate.get("is_default"):
                    return {
                        "id": rate["id"],
                        "rate": rate["rate"],
                        "name": rate["name"],
                    }
    except Exception:
        pass
    return None


def restore_default_tax_rate(auth_headers: dict, saved: dict | None) -> None:
    """Restore previously saved default tax rate, or clear default if none existed."""
    if saved is None:
        return
    try:
        # Remove default from all rates first
        rates_resp = httpx.get(
            f"{SERVER_URL}/api/tax-rates", headers=auth_headers, timeout=10
        )
        if rates_resp.status_code == 200:
            for rate in rates_resp.json().get("tax_rates", []):
                if rate.get("is_default") and rate["id"] != saved.get("id"):
                    httpx.put(
                        f"{SERVER_URL}/api/tax-rates/{rate['id']}",
                        json={
                            "name": rate["name"],
                            "rate": rate["rate"],
                            "is_default": False,
                        },
                        headers=auth_headers,
                        timeout=10,
                    )
        # Restore the saved rate as default
        httpx.put(
            f"{SERVER_URL}/api/tax-rates/{saved['id']}",
            json={"name": saved["name"], "rate": saved["rate"], "is_default": True},
            headers=auth_headers,
            timeout=10,
        )
    except Exception:
        pass
