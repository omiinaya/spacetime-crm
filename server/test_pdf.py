"""
Tests for server/pdf.py.

Tests HTML-to-PDF conversion using Playwright.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from server.pdf import html_to_pdf


class TestPdf:
    """Test suite for pdf.py."""

    @pytest.mark.asyncio
    async def test_html_to_pdf_returns_bytes(self):
        """html_to_pdf returns bytes."""
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF-1.4 mock pdf content"
        mock_page.set_content = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = AsyncMock()

        mock_chromium = MagicMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = MagicMock()
        mock_pw.chromium = mock_chromium

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("server.pdf.async_playwright", return_value=mock_cm):
            result = await html_to_pdf("<html><body>Test</body></html>")
            assert isinstance(result, bytes)
            assert result.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_html_to_pdf_sets_content(self):
        """html_to_pdf calls set_content with the HTML."""
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF content"
        mock_page.set_content = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = AsyncMock()

        mock_chromium = MagicMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = MagicMock()
        mock_pw.chromium = mock_chromium

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("server.pdf.async_playwright", return_value=mock_cm):
            await html_to_pdf("<html><body>Test</body></html>")
            mock_page.set_content.assert_called_once_with(
                "<html><body>Test</body></html>",
                wait_until="networkidle",
            )

    @pytest.mark.asyncio
    async def test_html_to_pdf_uses_letter_format(self):
        """html_to_pdf uses Letter format with 0.75in margins."""
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF content"
        mock_page.set_content = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = AsyncMock()

        mock_chromium = MagicMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = MagicMock()
        mock_pw.chromium = mock_chromium

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("server.pdf.async_playwright", return_value=mock_cm):
            await html_to_pdf("<html/>")
            mock_page.pdf.assert_called_once_with(
                format="Letter",
                margin={
                    "top": "0.75in",
                    "right": "0.75in",
                    "bottom": "0.75in",
                    "left": "0.75in",
                },
            )

    @pytest.mark.asyncio
    async def test_html_to_pdf_closes_browser(self):
        """html_to_pdf closes the browser after generating PDF."""
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF content"
        mock_page.set_content = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = AsyncMock()

        mock_chromium = MagicMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = MagicMock()
        mock_pw.chromium = mock_chromium

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("server.pdf.async_playwright", return_value=mock_cm):
            await html_to_pdf("<html/>")
            mock_browser.close.assert_called_once()
