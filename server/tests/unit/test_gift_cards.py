"""Unit tests for gift card route logic — tests the actual route functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from routes.gift_cards import _generate_gift_code, redeem_gift_card, void_gift_card

USER = {"id": "user_1", "tenant_id": "tenant_1", "name": "Test User"}


class TestGenerateGiftCode:
    """Test the gift card code generation utility."""

    def test_starts_with_gc_prefix(self):
        code = _generate_gift_code()
        assert code.startswith("GC-")

    def test_default_length(self):
        code = _generate_gift_code()
        # "GC-" prefix (3) + 12 chars = 15 total
        assert len(code) == 15

    def test_custom_length(self):
        code = _generate_gift_code(length=8)
        assert len(code) == 11  # GC- + 8

    def test_uppercase_alphanumeric(self):
        for _ in range(100):
            code = _generate_gift_code()
            suffix = code[3:]
            assert suffix.isalnum(), f"Non-alphanumeric suffix: {suffix}"
            assert suffix.isupper(), f"Not uppercase: {suffix}"

    def test_unique_codes(self):
        codes = {_generate_gift_code() for _ in range(1000)}
        assert len(codes) == 1000


class TestRedeemRoute:
    """Test the actual redeem_gift_card route function with mocked deps."""

    async def test_redeem_missing_code(self):
        """Empty code should fail with 400."""
        with pytest.raises(HTTPException) as exc:
            await redeem_gift_card({"code": "", "amount": 10}, USER)
        assert exc.value.status_code == 400

    async def test_redeem_invalid_amount(self):
        """Non-positive amounts should fail with 400."""
        for amount in [0, -1]:
            with pytest.raises(HTTPException) as exc:
                await redeem_gift_card({"code": "GC-XYZ", "amount": amount}, USER)
            assert exc.value.status_code == 400

    async def test_redeem_nonexistent_card(self):
        """Unknown code should fail with 404."""
        with patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(HTTPException) as exc:
                await redeem_gift_card({"code": "GC-NOPE", "amount": 10}, USER)
            assert exc.value.status_code == 404

    async def test_redeem_inactive_card(self):
        """Inactive card should fail with 400."""
        card = {
            "id": "gc_1",
            "code": "GC-OLD",
            "active": False,
            "expires_at": 0,
            "remaining_balance": 100.0,
        }
        with patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]):
            with pytest.raises(HTTPException) as exc:
                await redeem_gift_card({"code": "GC-OLD", "amount": 10}, USER)
            assert exc.value.status_code == 400
            assert "no longer active" in exc.value.detail

    async def test_redeem_expired_card(self):
        """Expired card should fail with 400 (uses real epoch time)."""
        card = {
            "id": "gc_1",
            "code": "GC-EXPIRED",
            "active": True,
            "expires_at": 1,  # long in the past
            "remaining_balance": 100.0,
        }
        with patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]):
            with pytest.raises(HTTPException) as exc:
                await redeem_gift_card({"code": "GC-EXPIRED", "amount": 10}, USER)
            assert exc.value.status_code == 400
            assert "expired" in exc.value.detail

    async def test_redeem_future_expiry_passes(self):
        """A card expiring in the future should NOT be rejected."""
        import time

        card = {
            "id": "gc_1",
            "code": "GC-FUTURE",
            "active": True,
            "expires_at": int((time.time() + 86400 * 30) * 1000),  # 30 days from now
            "remaining_balance": 100.0,
        }
        with (
            patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]),
            patch("routes.gift_cards._call", new_callable=AsyncMock, return_value={}),
            patch("routes.gift_cards._log_audit", new_callable=AsyncMock),
        ):
            result = await redeem_gift_card({"code": "GC-FUTURE", "amount": 10}, USER)
            assert result["ok"] is True
            assert result["redeemed"] == 10

    async def test_redeem_insufficient_balance(self):
        """Balance check should reject overspend with 400."""
        card = {
            "id": "gc_1",
            "code": "GC-LOW",
            "active": True,
            "expires_at": 0,
            "remaining_balance": 10.0,
        }
        with patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]):
            with pytest.raises(HTTPException) as exc:
                await redeem_gift_card({"code": "GC-LOW", "amount": 25}, USER)
            assert exc.value.status_code == 400
            assert "Insufficient balance" in exc.value.detail

    async def test_redeem_calls_reducer_and_audits(self):
        """Valid redemption calls the reducer and writes an audit log."""

        card = {
            "id": "gc_1",
            "code": "GC-OK",
            "active": True,
            "expires_at": 0,
            "remaining_balance": 100.0,
        }
        mock_call = AsyncMock(return_value={"ok": True})
        mock_audit = AsyncMock()
        with (
            patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]),
            patch("routes.gift_cards._call", mock_call),
            patch("routes.gift_cards._log_audit", mock_audit),
        ):
            result = await redeem_gift_card({"code": "GC-OK", "amount": 25}, USER)
            assert result["remaining"] == 75.0
            mock_call.assert_awaited_once_with("redeem_gift_card", ["gc_1", 25])
            mock_audit.assert_awaited_once()
            audit_args = mock_audit.call_args[0]
            assert audit_args[1] == "redeem"
            assert audit_args[2] == "gift_card"
            assert audit_args[3] == "GC-OK"

    async def test_redeem_reducer_502_becomes_400(self):
        """A reducer-level failure (race) surfaces as 400, not 502."""
        card = {
            "id": "gc_1",
            "code": "GC-RACE",
            "active": True,
            "expires_at": 0,
            "remaining_balance": 50.0,
        }
        with (
            patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]),
            patch(
                "routes.gift_cards._call",
                AsyncMock(side_effect=HTTPException(502, "Reducer call failed")),
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await redeem_gift_card({"code": "GC-RACE", "amount": 25}, USER)
            assert exc.value.status_code == 400


class TestVoidRoute:
    """Test the actual void_gift_card route function with mocked deps."""

    async def test_void_nonexistent_card_404(self):
        """Voiding an unknown (or other-tenant) card should fail with 404."""
        with patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(HTTPException) as exc:
                await void_gift_card("gc_unknown", USER)
            assert exc.value.status_code == 404

    async def test_void_other_tenant_card_404(self):
        """Tenant isolation: a card belonging to another tenant is not visible."""
        # The route queries with tenant_id = 'tenant_1', so another tenant's
        # card simply won't be returned by _sql → 404.
        with patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(HTTPException) as exc:
                await void_gift_card("gc_other", USER)
            assert exc.value.status_code == 404

    async def test_void_already_voided_card_400(self):
        """Double void should fail with 400."""
        card = {
            "id": "gc_1",
            "code": "GC-VOIDED",
            "tenant_id": "tenant_1",
            "active": False,
        }
        with patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]):
            with pytest.raises(HTTPException) as exc:
                await void_gift_card("gc_1", USER)
            assert exc.value.status_code == 400
            assert "already voided" in exc.value.detail

    async def test_void_valid_card_calls_reducer_and_audits(self):
        """Valid void calls the reducer scoped to the caller's tenant."""
        card = {
            "id": "gc_1",
            "code": "GC-VOID",
            "tenant_id": "tenant_1",
            "active": True,
        }
        mock_call = AsyncMock(return_value={"ok": True})
        mock_audit = AsyncMock()
        with (
            patch("routes.gift_cards._sql", new_callable=AsyncMock, return_value=[card]),
            patch("routes.gift_cards._call", mock_call),
            patch("routes.gift_cards._log_audit", mock_audit),
        ):
            result = await void_gift_card("gc_1", USER)
            assert result["ok"] is True
            mock_call.assert_awaited_once_with("void_gift_card", ["gc_1"])
            mock_audit.assert_awaited_once()
            audit_args = mock_audit.call_args[0]
            assert audit_args[1] == "void"
