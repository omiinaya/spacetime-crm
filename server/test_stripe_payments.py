"""
Tests for server/stripe_payments.py.

Tests Stripe payment processing: checkout sessions, webhooks, payment intents.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.stripe_payments import (
    is_configured,
    init_stripe,
    create_checkout_session,
    verify_webhook,
    create_setup_intent,
    create_payment_intent,
)


class TestStripePayments:
    """Test suite for stripe_payments.py."""

    def test_is_configured_returns_false_when_no_key(self):
        with patch("config.settings.stripe_secret_key", ""):
            assert is_configured() is False

    def test_is_configured_returns_true_when_key_set(self):
        with patch("config.settings.stripe_secret_key", "sk_test_123"):
            assert is_configured() is True

    def test_init_stripe_sets_api_key(self):
        import stripe as stripe_lib

        with patch("config.settings.stripe_secret_key", "sk_test_xyz"):
            init_stripe()
            assert stripe_lib.api_key == "sk_test_xyz"

    def test_init_stripe_no_key(self):
        with patch("config.settings.stripe_secret_key", ""):
            init_stripe()

    @pytest.mark.asyncio
    async def test_create_checkout_session_not_configured(self):
        with patch("server.stripe_payments.is_configured", return_value=False):
            result = await create_checkout_session(
                "inv1",
                1001,
                "cust1",
                "a@b.com",
                50.00,
                "Test items",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_create_checkout_session_success(self):
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/cs_test_123"

        with patch("server.stripe_payments.is_configured", return_value=True):
            with patch("server.stripe_payments.init_stripe"):
                with patch("stripe.checkout.Session.create", return_value=mock_session):
                    result = await create_checkout_session(
                        "inv1",
                        1001,
                        "cust1",
                        "a@b.com",
                        50.00,
                        "Test items",
                    )
                    assert result["session_id"] == "cs_test_123"
                    assert result["url"] == "https://checkout.stripe.com/cs_test_123"

    @pytest.mark.asyncio
    async def test_create_checkout_session_error(self):
        import stripe as stripe_lib

        with patch("server.stripe_payments.is_configured", return_value=True):
            with patch("server.stripe_payments.init_stripe"):
                with patch(
                    "stripe.checkout.Session.create",
                    side_effect=stripe_lib.StripeError("fail"),
                ):
                    result = await create_checkout_session(
                        "inv1",
                        1001,
                        "cust1",
                        "a@b.com",
                        50.00,
                        "Test",
                    )
                    assert result is None

    @pytest.mark.asyncio
    async def test_verify_webhook_not_configured(self):
        with patch("config.settings.stripe_webhook_secret", ""):
            result = await verify_webhook(b"{}", "sig123")
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_webhook_success(self):
        mock_event = MagicMock()
        mock_event.to_dict_recursive.return_value = {"type": "payment_intent.succeeded"}

        with patch("config.settings.stripe_webhook_secret", "whsec_123"):
            with patch("server.stripe_payments.init_stripe"):
                with patch("stripe.Webhook.construct_event", return_value=mock_event):
                    result = await verify_webhook(b"{}", "sig123")
                    assert result == {"type": "payment_intent.succeeded"}

    @pytest.mark.asyncio
    async def test_verify_webhook_invalid_signature(self):
        import stripe as stripe_lib

        with patch("config.settings.stripe_webhook_secret", "whsec_123"):
            with patch("server.stripe_payments.init_stripe"):
                with patch(
                    "stripe.Webhook.construct_event",
                    side_effect=stripe_lib.StripeError("bad sig"),
                ):
                    result = await verify_webhook(b"{}", "sig123")
                    assert result is None

    @pytest.mark.asyncio
    async def test_create_setup_intent_not_configured(self):
        with patch("server.stripe_payments.is_configured", return_value=False):
            result = await create_setup_intent("cust1")
            assert result is None

    @pytest.mark.asyncio
    async def test_create_setup_intent_success(self):
        mock_intent = MagicMock()
        mock_intent.client_secret = "seti_secret_123"
        mock_intent.id = "seti_123"

        with patch("server.stripe_payments.is_configured", return_value=True):
            with patch("server.stripe_payments.init_stripe"):
                with patch("stripe.SetupIntent.create", return_value=mock_intent):
                    result = await create_setup_intent("cust1")
                    assert result["client_secret"] == "seti_secret_123"
                    assert result["id"] == "seti_123"

    @pytest.mark.asyncio
    async def test_create_payment_intent_not_configured(self):
        with patch("server.stripe_payments.is_configured", return_value=False):
            result = await create_payment_intent(
                "inv1",
                1001,
                "a@b.com",
                50.00,
                "pm_123",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self):
        mock_intent = MagicMock()
        mock_intent.id = "pi_123"
        mock_intent.status = "succeeded"

        with patch("server.stripe_payments.is_configured", return_value=True):
            with patch("server.stripe_payments.init_stripe"):
                with patch("stripe.PaymentIntent.create", return_value=mock_intent):
                    result = await create_payment_intent(
                        "inv1",
                        1001,
                        "a@b.com",
                        50.00,
                        "pm_123",
                    )
                    assert result["payment_intent_id"] == "pi_123"
                    assert result["status"] == "succeeded"
