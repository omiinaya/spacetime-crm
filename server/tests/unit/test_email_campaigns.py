"""Unit tests for email campaign route logic — tests the actual route function."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from routes.email_campaigns import send_email_blast

USER = {"id": "user_1", "tenant_id": "tenant_1", "name": "Test User"}

VALID_BODY = {
    "subject": "Spring Sale!",
    "html_body": "<h1>Hello {{name}}!</h1>",
    "customer_filter": "all",
}


class TestSendBlastValidation:
    """Test validation in the actual send_email_blast route."""

    async def test_requires_subject(self):
        with pytest.raises(HTTPException) as exc:
            await send_email_blast({"subject": "", "html_body": "<p>x</p>"}, USER)
        assert exc.value.status_code == 400

    async def test_requires_body(self):
        with pytest.raises(HTTPException) as exc:
            await send_email_blast({"subject": "S", "html_body": "  "}, USER)
        assert exc.value.status_code == 400

    async def test_accepts_valid_input(self):
        with (
            patch("routes.email_campaigns._sql", new_callable=AsyncMock) as mock_sql,
            patch("routes.email_campaigns.send_email", return_value=True),
        ):
            mock_sql.return_value = [
                {"id": "c1", "first_name": "Alice", "last_name": "J", "email": "a@test.com"}
            ]
            result = await send_email_blast(VALID_BODY, USER)
            assert result["ok"] is True
            assert result["sent"] == 1


class TestTestMode:
    """Test-mode sends a single email to a given address."""

    async def test_test_mode_sends_to_one_address(self):
        with patch("routes.email_campaigns.send_email", return_value=True) as mock_send:
            result = await send_email_blast({**VALID_BODY, "send_test_only": "boss@test.com"}, USER)
            assert result["mode"] == "test"
            assert result["sent"] == 1
            assert result["recipients"] == ["boss@test.com"]
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[0] == "boss@test.com"
            assert args[1] == "Spring Sale!"

    async def test_test_mode_failure_raises_500(self):
        with patch("routes.email_campaigns.send_email", return_value=False):
            with pytest.raises(HTTPException) as exc:
                await send_email_blast({**VALID_BODY, "send_test_only": "boss@test.com"}, USER)
            assert exc.value.status_code == 500


class TestRecipientFiltering:
    """Recipient queries and filter behavior."""

    async def test_all_filter_requires_email_column(self):
        """'all' filter always appends the email-not-null clause."""
        with (
            patch("routes.email_campaigns._sql", new_callable=AsyncMock) as mock_sql,
            patch("routes.email_campaigns.send_email", return_value=True),
        ):
            mock_sql.return_value = [
                {"id": "c1", "first_name": "A", "last_name": "B", "email": "a@test.com"}
            ]
            await send_email_blast(VALID_BODY, USER)
            query = mock_sql.call_args[0][0]
            assert "email IS NOT NULL AND email != ''" in query
            assert "tenant_id = 'tenant_1'" in query

    async def test_recent_filter_uses_real_epoch_cutoff(self):
        """Regression: the recent cutoff must be real epoch ms, not monotonic.

        Previously used asyncio.get_event_loop().time()*1000 (monotonic),
        which produced a cutoff of ~123000 ms → the created_at >= cutoff
        clause matched EVERY ticket, making the 'recent' filter useless.
        """
        with (
            patch("routes.email_campaigns._sql", new_callable=AsyncMock) as mock_sql,
            patch("routes.email_campaigns.send_email", return_value=True),
        ):
            mock_sql.return_value = [
                {"id": "c1", "first_name": "A", "last_name": "B", "email": "a@test.com"}
            ]
            days = 30
            await send_email_blast(
                {**VALID_BODY, "customer_filter": "recent", "days_since_last": days}, USER
            )
            query = mock_sql.call_args[0][0]
            # Extract the numeric cutoff from the query
            import re

            match = re.search(r"created_at >= (\d+)", query)
            assert match, f"No cutoff found in query: {query}"
            cutoff = int(match.group(1))
            now_ms = int(time.time() * 1000)
            expected = now_ms - (days * 86400 * 1000)
            # Allow a small drift between building the query and asserting
            assert abs(cutoff - expected) < 5000, f"cutoff={cutoff} expected≈{expected}"

    async def test_no_matching_customers_raises_400(self):
        with patch("routes.email_campaigns._sql", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(HTTPException) as exc:
                await send_email_blast(VALID_BODY, USER)
            assert exc.value.status_code == 400
            assert "No customers match" in exc.value.detail


class TestBlastDelivery:
    """Full blast delivery behavior."""

    async def test_personalizes_and_sends_to_each_customer(self):
        customers = [
            {"id": "c1", "first_name": "Alice", "last_name": "J", "email": "a@test.com"},
            {"id": "c2", "first_name": "Bob", "last_name": "S", "email": "b@test.com"},
            {"id": "c3", "first_name": "", "last_name": "", "email": "c@test.com"},
        ]
        with (
            patch("routes.email_campaigns._sql", new_callable=AsyncMock, return_value=customers),
            patch("routes.email_campaigns.send_email", return_value=True) as mock_send,
        ):
            result = await send_email_blast(VALID_BODY, USER)
            assert result["sent"] == 3
            assert result["total_matched"] == 3
            assert mock_send.call_count == 3

            # First customer: name personalized
            body1 = mock_send.call_args_list[0].args[2]
            assert "Alice J" in body1
            # Third customer: no name → Valued Customer
            body3 = mock_send.call_args_list[2].args[2]
            assert "Valued Customer" in body3

    async def test_counts_failures(self):
        customers = [
            {"id": "c1", "first_name": "A", "last_name": "B", "email": "a@test.com"},
            {"id": "c2", "first_name": "C", "last_name": "D", "email": "b@test.com"},
        ]
        with (
            patch("routes.email_campaigns._sql", new_callable=AsyncMock, return_value=customers),
            patch("routes.email_campaigns.send_email", side_effect=[True, False]),
        ):
            result = await send_email_blast(VALID_BODY, USER)
            assert result["sent"] == 1
            assert result["failed"] == 1

    async def test_skips_rows_without_email(self):
        customers = [
            {"id": "c1", "first_name": "A", "last_name": "B", "email": ""},
            {"id": "c2", "first_name": "C", "last_name": "D", "email": "  "},
            {"id": "c3", "first_name": "E", "last_name": "F", "email": "e@test.com"},
        ]
        with (
            patch("routes.email_campaigns._sql", new_callable=AsyncMock, return_value=customers),
            patch("routes.email_campaigns.send_email", return_value=True) as mock_send,
        ):
            result = await send_email_blast(VALID_BODY, USER)
            assert result["sent"] == 1
            mock_send.assert_called_once()
