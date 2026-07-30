"""Report schedule helpers — next-run calculation and HTML email rendering.

Extracted from report_helpers.py for cleaner separation.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def _calc_next_run(frequency: str, config: dict, from_ms: int) -> int:
    """Calculate the next run timestamp based on frequency and config."""
    dt = datetime.fromtimestamp(from_ms / 1000)
    hour = config.get("hour", 8)
    minute = config.get("minute", 0)

    if frequency == "daily":
        next_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_dt <= dt:
            next_dt += timedelta(days=1)
    elif frequency == "weekly":
        day_of_week = config.get("day_of_week", 0)  # 0=Monday
        next_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (day_of_week - next_dt.weekday()) % 7
        if days_ahead == 0 and next_dt <= dt:
            days_ahead = 7
        next_dt += timedelta(days=days_ahead)
    elif frequency == "monthly":
        day_of_month = min(config.get("day_of_month", 1), 28)
        next_dt = dt.replace(
            day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0
        )
        if next_dt <= dt:
            if next_dt.month == 12:
                next_dt = next_dt.replace(year=next_dt.year + 1, month=1)
            else:
                next_dt = next_dt.replace(month=next_dt.month + 1)
    else:
        next_dt = dt + timedelta(days=1)

    return int(next_dt.timestamp() * 1000)


def _render_report_email(report_type: str, name: str, data: dict) -> str:
    """Render report data as an HTML email body."""
    rows_html = ""
    for r in data.get("rows", []):
        rows_html += "<tr>"
        for cell in r:
            val = str(cell) if cell is not None else ""
            rows_html += (
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{val}</td>"
            )
        rows_html += "</tr>"

    summary_html = ""
    if data.get("type") == "revenue":
        summary_html = f"""
        <div style="margin-bottom:16px">
          <p><strong>Total Revenue:</strong> ${data.get("total_revenue", 0):,.2f}</p>
          <p><strong>Invoice Count:</strong> {data.get("invoice_count", 0)}</p>
          <p><strong>Period:</strong> {data.get("period", "all")}</p>
        </div>"""
    elif data.get("type") == "tickets":
        summary_html = f"""
        <div style="margin-bottom:16px">
          <p><strong>Total Tickets:</strong> {data.get("total", 0)}</p>
          <p><strong>Open:</strong> {data.get("open", 0)}</p>
        </div>"""
    elif data.get("type") == "payments":
        summary_html = f"""
        <div style="margin-bottom:16px">
          <p><strong>Total Collected:</strong> ${data.get("total_collected", 0):,.2f}</p>
          <p><strong>Payments:</strong> {data.get("payment_count", 0)}</p>
        </div>"""
    elif data.get("type") in ("inventory", "products"):
        summary_html = f"""
        <div style="margin-bottom:16px">
          <p><strong>Total Products:</strong> {data.get("total_products", 0)}</p>
          <p><strong>Low Stock:</strong> {data.get("low_stock_count", 0)}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;padding:20px;background:#f5f5f5">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:8px;padding:24px">
<div style="border-bottom:2px solid #0070f3;padding-bottom:12px;margin-bottom:16px">
<h2 style="margin:0;color:#333">{name}</h2>
<p style="margin:4px 0 0;color:#666;font-size:12px">
  Generated {datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")}
</p>
</div>
{summary_html}
<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead>
<tr style="background:#f9f9f9">
<th style="padding:8px 10px;text-align:left;border-bottom:2px solid #ddd">Item</th>
<th style="padding:8px 10px;text-align:left;border-bottom:2px solid #ddd">Value</th>
<th style="padding:8px 10px;text-align:left;border-bottom:2px solid #ddd">Status</th>
<th style="padding:8px 10px;text-align:left;border-bottom:2px solid #ddd">Date</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
<p style="color:#999;font-size:11px;margin-top:24px;text-align:center">
SpacetimeCRM · Automated Report Delivery
</p>
</div></body></html>"""
