"""Unit tests for helpers._log_audit."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ===================================================================
# _log_audit
# ===================================================================


class TestLogAudit:
    """Fire-and-forget audit logging via _call."""

    @pytest.mark.asyncio
    async def test_logs_successfully(self) -> None:
        """Should call _call with audit params."""
        with patch("helpers._call", new_callable=AsyncMock) as mock_call:
            from helpers import _log_audit

            await _log_audit(
                {"tenant_id": "t-1", "id": "u-1", "name": "Admin"},
                "update",
                "invoice",
                "inv-001",
                "Changed status",
            )

        mock_call.assert_called_once_with(
            "log_audit",
            [
                "t-1",
                "u-1",
                "Admin",
                "update",
                "invoice",
                "inv-001",
                "Changed status",
            ],
        )

    @pytest.mark.asyncio
    async def test_fallback_for_missing_user_keys(self) -> None:
        """Should use empty strings for missing user fields."""
        with patch("helpers._call", new_callable=AsyncMock) as mock_call:
            from helpers import _log_audit

            await _log_audit({}, "delete", "user", "u-99")

        mock_call.assert_called_once_with(
            "log_audit",
            [
                "",
                "",
                "",
                "delete",
                "user",
                "u-99",
                "",
            ],
        )

    @pytest.mark.asyncio
    async def test_never_raises(self) -> None:
        """Should catch and log exceptions, never raise."""
        with patch("helpers._call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = RuntimeError("DB down")
            from helpers import _log_audit

            # Should not raise
            await _log_audit(
                {"tenant_id": "t-1", "id": "u-1", "name": "Admin"},
                "delete",
                "customer",
                "c-1",
            )
        # If we got here, no exception was raised
