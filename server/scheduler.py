"""Background scheduler — in-process periodic tasks.

Replaces ALL external Hermes cron jobs for CRM lifecycle management.

Design:
  - Runs as asyncio tasks inside the FastAPI server process
  - Each periodic function calls existing API endpoints (no logic duplication)
  - Self-contained — no external dependencies

Scheduler loops:
  overdue_check        :3600s  — trigger overdue check + send reminders
  recurring_invoices   :86400s — generate invoices from recurring templates
  appointment_reminders:3600s  — send 24h appointment reminders
  low_stock_alerts     :3600s  — detect low stock, log alert
  log_cleanup          :86400s — archive old audit logs
"""

import asyncio
import logging

import httpx

logger = logging.getLogger("spacetime-crm.scheduler")

# Reuse a single httpx client for all scheduler calls
_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url="http://localhost:8723",
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
    return _client


# ── Scheduled tasks ─────────────────────────────────────────────


async def overdue_check(interval: int):
    """Detect overdue invoices and send notifications.

    Calls the existing API endpoints: trigger-overdue-check then send-overdue-reminders.
    """
    while True:
        try:
            await asyncio.sleep(interval)

            client = _http()
            # Step 1: Mark invoices as overdue
            resp1 = await client.post("/api/invoices/trigger-overdue-check")
            if resp1.status_code == 200:
                data1 = resp1.json()
                logger.info(
                    f"[scheduler:overdue] Check complete: {data1.get('overdue_count', 0)} overdue, "
                    f"${data1.get('overdue_total', 0):.2f} total"
                )
            else:
                logger.warning(
                    f"[scheduler:overdue] trigger-overdue-check returned {resp1.status_code}"
                )

            # Step 2: Send reminders for overdue invoices
            resp2 = await client.post("/api/invoices/send-overdue-reminders")
            if resp2.status_code == 200:
                data2 = resp2.json()
                notified = data2.get("notified", data2.get("total_sent", 0))
                if notified:
                    logger.info(f"[scheduler:overdue] Sent {notified} overdue reminders")
            else:
                logger.warning(
                    f"[scheduler:overdue] send-overdue-reminders returned {resp2.status_code}"
                )

        except asyncio.CancelledError:
            break
        except httpx.ConnectError:
            logger.debug("[scheduler:overdue] Server not ready yet, skipping")
        except Exception as e:
            logger.error(f"[scheduler:overdue] Error: {e}", exc_info=True)


async def recurring_invoices(interval: int):
    """Generate invoices from recurring templates.

    Calls the existing /api/recurring-invoices/generate endpoint.
    """
    while True:
        try:
            await asyncio.sleep(interval)

            client = _http()
            resp = await client.post("/api/recurring-invoices/generate")
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("generated", data.get("count", 0))
                if count:
                    logger.info(f"[scheduler:recurring] Generated {count} invoices")
                else:
                    logger.debug("[scheduler:recurring] No invoices due for generation")
            else:
                logger.warning(f"[scheduler:recurring] generate returned {resp.status_code}")

        except asyncio.CancelledError:
            break
        except httpx.ConnectError:
            logger.debug("[scheduler:recurring] Server not ready yet, skipping")
        except Exception as e:
            logger.error(f"[scheduler:recurring] Error: {e}", exc_info=True)


async def appointment_reminders(interval: int):
    """Send 24h appointment reminders.

    Calls the existing /api/appointments/send-reminders endpoint.
    """
    while True:
        try:
            await asyncio.sleep(interval)

            client = _http()
            resp = await client.post("/api/appointments/send-reminders")
            if resp.status_code == 200:
                data = resp.json()
                sent = data.get("sent", data.get("notified", data.get("count", 0)))
                if sent:
                    logger.info(f"[scheduler:appointments] Sent {sent} reminders")
            else:
                logger.warning(
                    f"[scheduler:appointments] send-reminders returned {resp.status_code}"
                )

        except asyncio.CancelledError:
            break
        except httpx.ConnectError:
            logger.debug("[scheduler:appointments] Server not ready yet, skipping")
        except Exception as e:
            logger.error(f"[scheduler:appointments] Error: {e}", exc_info=True)


async def low_stock_alerts(interval: int):
    """Detect low stock products and log alerts.

    Calls the existing /api/products/low-stock endpoint.
    """
    while True:
        try:
            await asyncio.sleep(interval)

            client = _http()
            resp = await client.get("/api/products/low-stock")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for prod in data:
                        logger.warning(
                            f"[scheduler:lowstock] Low stock: {prod.get('name', '?')} "
                            f"(id={prod.get('id', '?')}) — "
                            f"{prod.get('quantity_on_hand', 0)} remaining"
                        )
                elif isinstance(data, dict):
                    count = data.get("count", data.get("total", 0))
                    if count:
                        logger.warning(f"[scheduler:lowstock] {count} low-stock products detected")
            else:
                logger.debug("[scheduler:lowstock] No low-stock endpoint or empty")

        except asyncio.CancelledError:
            break
        except httpx.ConnectError:
            logger.debug("[scheduler:lowstock] Server not ready yet, skipping")
        except Exception as e:
            logger.error(f"[scheduler:lowstock] Error: {e}", exc_info=True)


async def log_cleanup(interval: int):
    """Archive audit logs older than 90 days."""
    while True:
        try:
            await asyncio.sleep(interval)

            client = _http()
            resp = await client.delete("/api/audit-logs/cleanup?days=90")
            if resp.status_code == 200:
                data = resp.json()
                deleted = data.get("deleted", data.get("count", 0))
                if deleted:
                    logger.info(f"[scheduler:cleanup] Archived {deleted} old audit log entries")
            else:
                logger.debug("[scheduler:cleanup] No cleanup endpoint or empty")

        except asyncio.CancelledError:
            break
        except httpx.ConnectError:
            logger.debug("[scheduler:cleanup] Server not ready yet, skipping")
        except Exception as e:
            logger.error(f"[scheduler:cleanup] Error: {e}", exc_info=True)


# ── Config ──────────────────────────────────────────────────────

SCHEDULED_TASKS = {
    "overdue_check": (overdue_check, 3600),  # hourly
    "recurring_invoices": (recurring_invoices, 86400),  # daily
    "appointment_reminders": (appointment_reminders, 3600),  # hourly
    "low_stock_alerts": (low_stock_alerts, 3600),  # hourly
    "log_cleanup": (log_cleanup, 86400),  # daily
}
