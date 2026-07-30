"""Unit tests for server/pdf.py.

Tests the html_to_pdf function with mocked Playwright to avoid
requiring a real Chromium installation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHtmlToPdf:
    """Tests for the html_to_pdf function using mocked Playwright."""

    @pytest.fixture
    def _mock_playwright(self):
        """Set up a complete mock of the playwright async context manager chain.

        The chain is:
            async_playwright() -> PlaywrightContextManager
            ctx.__aenter__() -> Playwright object (pw)
            pw.chromium.launch() -> Browser (async)
            browser.new_page() -> Page (async)
            page.set_content() -> None (async)
            page.pdf() -> bytes (async)
        """
        mock_page = AsyncMock()
        mock_page.set_content = AsyncMock()
        mock_page.pdf = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        mock_chromium = MagicMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_pw_ctx = AsyncMock()
        mock_pw_ctx.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_pw_ctx.__aexit__ = AsyncMock(return_value=None)

        return mock_pw_ctx, mock_page, mock_browser, mock_chromium

    @pytest.mark.asyncio
    async def test_html_to_pdf_returns_bytes(self, _mock_playwright) -> None:
        """Should return raw PDF bytes for valid HTML input."""
        mock_pw_ctx, mock_page, _mock_browser, _mock_chromium = _mock_playwright
        mock_page.pdf.return_value = b"%PDF-1.4 mock pdf content"

        with patch("pdf.async_playwright", return_value=mock_pw_ctx):
            from pdf import html_to_pdf

            pdf_bytes = await html_to_pdf("<html><body><p>Hello</p></body></html>")

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-1.4")
        mock_page.set_content.assert_awaited_once_with(
            "<html><body><p>Hello</p></body></html>",
            wait_until="networkidle",
        )
        mock_page.pdf.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pdf_uses_letter_format(self, _mock_playwright) -> None:
        """Should format the PDF as US Letter with 0.75in margins."""
        mock_pw_ctx, mock_page, _mock_browser, _mock_chromium = _mock_playwright
        mock_page.pdf.return_value = b"%PDF-1.4"

        with patch("pdf.async_playwright", return_value=mock_pw_ctx):
            from pdf import html_to_pdf

            await html_to_pdf("<html><body><p>Test</p></body></html>")

        mock_page.pdf.assert_awaited_once_with(
            format="Letter",
            margin={
                "top": "0.75in",
                "right": "0.75in",
                "bottom": "0.75in",
                "left": "0.75in",
            },
        )

    @pytest.mark.asyncio
    async def test_empty_html_renders(self, _mock_playwright) -> None:
        """Should handle empty HTML without crashing."""
        mock_pw_ctx, mock_page, _mock_browser, _mock_chromium = _mock_playwright
        mock_page.pdf.return_value = b"%PDF-1.4 minimal"

        with patch("pdf.async_playwright", return_value=mock_pw_ctx):
            from pdf import html_to_pdf

            pdf_bytes = await html_to_pdf("")
        assert isinstance(pdf_bytes, bytes)

    @pytest.mark.asyncio
    async def test_complex_html_pdf(self, _mock_playwright) -> None:
        """Should handle complex HTML with tables and CSS styles."""
        mock_pw_ctx, mock_page, _mock_browser, _mock_chromium = _mock_playwright
        mock_page.pdf.return_value = b"%PDF-1.4 complex"

        complex_html = """<!DOCTYPE html>
<html><head><style>
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid black; padding: 8px; }
</style></head><body>
  <h1>Invoice #123</h1>
  <table><tr><th>Item</th><th>Price</th></tr>
  <tr><td>Widget</td><td>$10.00</td></tr></table>
</body></html>"""

        with patch("pdf.async_playwright", return_value=mock_pw_ctx):
            from pdf import html_to_pdf

            pdf_bytes = await html_to_pdf(complex_html)
        assert isinstance(pdf_bytes, bytes)
        mock_page.set_content.assert_awaited_once_with(
            complex_html, wait_until="networkidle"
        )

    @pytest.mark.asyncio
    async def test_browser_closed_after_pdf(self, _mock_playwright) -> None:
        """Browser should be closed after PDF generation."""
        mock_pw_ctx, mock_page, mock_browser, _mock_chromium = _mock_playwright
        mock_page.pdf.return_value = b"%PDF-1.4"

        with patch("pdf.async_playwright", return_value=mock_pw_ctx):
            from pdf import html_to_pdf

            await html_to_pdf("<p>Test</p>")

        mock_browser.close.assert_awaited_once()
