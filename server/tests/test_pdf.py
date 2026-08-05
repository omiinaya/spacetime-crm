"""Tests for pdf module (Playwright HTML-to-PDF conversion)."""

from unittest.mock import AsyncMock, patch

import pytest

from pdf import html_to_pdf


class TestHtmlToPdf:
    @pytest.mark.asyncio
    async def test_returns_bytes(self):
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF-1.4 mock pdf content"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        # Patch the async_playwright context manager
        with patch("pdf.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__.return_value = mock_pw
            result = await html_to_pdf("<h1>Hello</h1>")

        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-1.4")

    @pytest.mark.asyncio
    async def test_sets_content_before_pdf(self):
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with patch("pdf.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__.return_value = mock_pw
            await html_to_pdf("<p>Test</p>")

        mock_page.set_content.assert_called_once_with("<p>Test</p>", wait_until="networkidle")

    @pytest.mark.asyncio
    async def test_uses_letter_format_and_margins(self):
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with patch("pdf.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__.return_value = mock_pw
            await html_to_pdf("<p>Test</p>")

        mock_page.pdf.assert_called_once_with(
            format="Letter",
            margin={"top": "0.75in", "right": "0.75in", "bottom": "0.75in", "left": "0.75in"},
        )

    @pytest.mark.asyncio
    async def test_closes_browser_after_pdf(self):
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with patch("pdf.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__.return_value = mock_pw
            await html_to_pdf("<p>Test</p>")

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_empty_html(self):
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"%PDF"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with patch("pdf.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__.return_value = mock_pw
            result = await html_to_pdf("")
            assert result == b"%PDF"
