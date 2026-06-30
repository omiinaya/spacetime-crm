"""PDF generation using Playwright + Chromium headless.

Replaced weasyprint to reduce Docker image size (~100MB+ savings from system deps).
Uses actual Chrome engine — full CSS support, including flexbox, @page, modern layout.
"""
from __future__ import annotations


async def html_to_pdf(html: str) -> bytes:
    """Convert an HTML string to PDF bytes using Chromium headless.

    Returns raw PDF bytes suitable for FastAPI Response(content=..., media_type="application/pdf").
    Page format matches US Letter with 0.75in margins.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf = await page.pdf(
            format="Letter",
            margin={
                "top": "0.75in",
                "right": "0.75in",
                "bottom": "0.75in",
                "left": "0.75in",
            },
        )
        await browser.close()
        return pdf
