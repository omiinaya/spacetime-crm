"""Report rendering engine — pure functions for building HTML report emails.

Extracted from routes/report_schedules.py for better testability and reuse.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def calc_next_run(frequency: str, config: dict, from_ms: int) -> int:
    """Calculate the next run timestamp based on frequency and config."""
    dt = datetime.fromtimestamp(from_ms / 1000, tz=timezone.utc)
    hour = config.get("hour", 8)
    minute = config.get("minute", 0)

    if frequency == "daily":
        next_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_dt <= dt:
            next_dt += timedelta(days=1)
    elif frequency == "weekly":
        day_of_week = config.get("day_of_week", 0)
        days_ahead = day_of_week - dt.weekday()
        if days_ahead < 0 or (days_ahead == 0 and (dt.hour > hour or (dt.hour == hour and dt.minute >= minute))):
            days_ahead += 7
        next_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    elif frequency == "monthly":
        day_of_month = config.get("day_of_month", 1)
        target_day = min(day_of_month, 28)
        try:
            next_dt = dt.replace(day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            next_dt = dt.replace(day=28, hour=hour, minute=minute, second=0, microsecond=0)
        if next_dt <= dt:
            month = dt.month + 1
            year = dt.year
            if month > 12:
                month = 1
                year += 1
            try:
                next_dt = dt.replace(
                    year=year, month=month, day=target_day, hour=hour, minute=minute, second=0, microsecond=0
                )
            except ValueError:
                next_dt = dt.replace(year=year, month=month, day=28, hour=hour, minute=minute, second=0, microsecond=0)
    else:
        next_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)

    return int(next_dt.timestamp() * 1000)


def render_report_email(report_type: str, name: str, data: dict) -> str:
    """Render report data as an HTML email."""
    metrics_html = "".join(
        f'<tr><td style="padding:8px 16px;border-bottom:1px solid #e5e7eb;color:#666">{m["label"]}</td>'
        f'<td style="padding:8px 16px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;color:#111">{m["value"]}</td></tr>'
        for m in data.get("metrics", [])
    )

    chart_html = ""
    if data.get("chart"):
        max_val = max((c["value"] for c in data["chart"]), default=1) or 1
        bars = "".join(
            f'<div style="display:flex;align-items:center;margin:4px 0">'
            f'<span style="width:80px;font-size:11px;color:#666;text-align:right;padding-right:8px">{c["label"]}</span>'
            f'<div style="flex:1;background:#f0f0f0;border-radius:4px;overflow:hidden;height:20px">'
            f'<div style="width:{max(c["value"] / max_val * 100, 5)}%;background:#3b82f6;height:20px;border-radius:4px;text-align:right;padding-right:4px;line-height:20px;font-size:10px;color:#fff;min-width:fit-content">'
            f"{c['value']}</div></div></div>"
            for c in data["chart"]
        )
        chart_html = f'<h3 style="color:#333;margin:20px 0 10px">{data.get("chart_label", "")}</h3>{bars}'

    chart2_html = ""
    if data.get("chart2"):
        max_val = max((c["value"] for c in data["chart2"]), default=1) or 1
        bars2 = "".join(
            f'<div style="display:flex;align-items:center;margin:4px 0">'
            f'<span style="width:120px;font-size:11px;color:#666;text-align:right;padding-right:8px">{c["label"]}</span>'
            f'<div style="flex:1;background:#f0f0f0;border-radius:4px;overflow:hidden;height:20px">'
            f'<div style="width:{max(c["value"] / max_val * 100, 5)}%;background:#22c55e;height:20px;border-radius:4px;text-align:right;padding-right:4px;line-height:20px;font-size:10px;color:#fff">'
            f"{c['value']}</div></div></div>"
            for c in data["chart2"]
        )
        chart2_html = f'<h3 style="color:#333;margin:20px 0 10px">{data.get("chart2_label", "")}</h3>{bars2}'

    extra_html = ""
    if data.get("chart2"):
        extra = data["chart2"][0].get("extra", "") if data["chart2"] else ""
        if extra:
            extra_html = f'<p style="color:#999;font-size:11px">{extra}</p>'

    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:640px;margin:0 auto;padding:20px;background:#f9fafb">
<div style="background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
<h1 style="font-size:20px;color:#111;margin:0 0 4px">📊 {data.get("title", name)}</h1>
<p style="color:#666;font-size:13px;margin:0 0 20px">{datetime.utcnow().strftime("%B %d, %Y")}</p>

<table style="width:100%;border-collapse:collapse;margin:16px 0;background:#f8f8ff;border-radius:8px">{metrics_html}</table>

{chart_html}
{chart2_html}
{extra_html}

<p style="color:#999;font-size:11px;margin-top:24px;text-align:center">
SpacetimeCRM · Automated Report Delivery
</p>
</div></body></html>"""
