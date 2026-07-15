"""Unit tests for stripe_payments module.

Note: stripe_lib methods are synchronous (not async), even though the
wrapper functions are async. So we mock with regular MagicMock, not AsyncMock.
"""

from __future__ import annotations

import sys
from pathlib import Path

_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from unittest.mock import MagicMock, patch

import pytest

from config import settings
from stripe_payments import (
    is_configured,
    init_stripe,
    create_checkout_session,
    create_setup_intent,
    create_payment_intent,
)


class TestIsConfigured:
    def test_configured_when_key_set(self):
        settings.stripe_secret_key = "sk_test_123"
        assert is_configured() is True

    def test_not_configured_when_key_empty(self):
        settings.stripe_secret_key = ""
        assert is_configured() is False


class TestInitStripe:
    def test_init_sets_api_key(self):
        settings.stripe_secret_key = "sk_test_abc"
        import stripe as stripe_lib

        stripe_lib.api_key = None
        init_stripe()
        assert stripe_lib.api_key == "sk_test_abc"


class TestCreateCheckoutSession:
    @pytest.mark.asyncio
    async def test_not_configured_returns_none(self):
        settings.stripe_secret_key = ""
        result = await create_checkout_session("inv1", 100, "cus_1", "a@b.com", 50.0, "desc")
        assert result is None

    @pytest.mark.asyncio
    async def test_successful(self, monkeypatch):
        settings.stripe_secret_key = "sk_test_123"
        mock_session = MagicMock(id="cs_test_abc", url="https://checkout.stripe.com/test")
        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.return_value = mock_session
        monkeypatch.setattr("stripe_payments.stripe_lib", mock_stripe)
        result = await create_checkout_session("inv1", 100, "cus_1", "a@b.com", 50.0, "desc")
        assert result == {"session_id": "cs_test_abc", "url": "https://checkout.stripe.com/test"}

    @pytest.mark.asyncio
    async def test_stripe_error(self, monkeypatch):
        settings.stripe_secret_key = "sk_test_123"
        from stripe import StripeError

        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.side_effect = StripeError("fail")
        monkeypatch.setattr("stripe_payments.stripe_lib", mock_stripe)
        result = await create_checkout_session("inv1", 100, "cus_1", "a@b.com", 50.0, "desc")
        assert result is None


class TestCreateSetupIntent:
    @pytest.mark.asyncio
    async def test_not_configured_returns_none(self):
        settings.stripe_secret_key = ""
        result = await create_setup_intent("cust_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_successful(self, monkeypatch):
        settings.stripe_secret_key = "sk_test_123"
        mock_intent = MagicMock(client_secret="seti_secret_abc", id="seti_123")
        mock_stripe = MagicMock()
        mock_stripe.SetupIntent.create.return_value = mock_intent
        monkeypatch.setattr("stripe_payments.stripe_lib", mock_stripe)
        result = await create_setup_intent("cust_1")
        assert result == {"client_secret": "seti_secret_abc", "id": "seti_123"}

    @pytest.mark.asyncio
    async def test_stripe_error(self, monkeypatch):
        settings.stripe_secret_key = "sk_test_123"
        from stripe import StripeError

        mock_stripe = MagicMock()
        mock_stripe.SetupIntent.create.side_effect = StripeError("fail")
        monkeypatch.setattr("stripe_payments.stripe_lib", mock_stripe)
        result = await create_setup_intent("cust_1")
        assert result is None


class TestCreatePaymentIntent:
    @pytest.mark.asyncio
    async def test_not_configured_returns_none(self):
        settings.stripe_secret_key = ""
        result = await create_payment_intent("inv1", 100, "a@b.com", 50.0, "pm_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_successful(self, monkeypatch):
        settings.stripe_secret_key = "sk_test_123"
        mock_intent = MagicMock(id="pi_123", status="succeeded")
        mock_stripe = MagicMock()
        mock_stripe.PaymentIntent.create.return_value = mock_intent
        monkeypatch.setattr("stripe_payments.stripe_lib", mock_stripe)
        result = await create_payment_intent("inv1", 100, "a@b.com", 50.0, "pm_1")
        assert result == {"payment_intent_id": "pi_123", "status": "succeeded", "amount": 50.0}

    @pytest.mark.asyncio
    async def test_stripe_error(self, monkeypatch):
        settings.stripe_secret_key = "sk_test_123"
        from stripe import StripeError

        mock_stripe = MagicMock()
        mock_stripe.PaymentIntent.create.side_effect = StripeError("fail")
        monkeypatch.setattr("stripe_payments.stripe_lib", mock_stripe)
        result = await create_payment_intent("inv1", 100, "a@b.com", 50.0, "pm_1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_zero_amount(self, monkeypatch):
        settings.stripe_secret_key = "sk_test_123"
        mock_intent = MagicMock(id="pi_zero", status="succeeded")
        mock_stripe = MagicMock()
        mock_stripe.PaymentIntent.create.return_value = mock_intent
        monkeypatch.setattr("stripe_payments.stripe_lib", mock_stripe)
        result = await create_payment_intent("inv0", 0, "no@charge.com", 0.0, "pm_0")
        assert result["amount"] == 0.0
