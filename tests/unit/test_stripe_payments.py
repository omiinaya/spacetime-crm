"""Tests for stripe_payments module (Stripe checkout, webhooks, intents)."""

from unittest.mock import patch, MagicMock

import pytest

from stripe_payments import (
    is_configured, init_stripe, create_checkout_session,
    verify_webhook, create_setup_intent, create_payment_intent,
)


class TestIsConfigured:
    def test_returns_false_when_no_key(self):
        with patch("stripe_payments.settings") as mock_settings:
            mock_settings.stripe_secret_key = ""
            assert is_configured() is False

    def test_returns_true_when_key_present(self):
        with patch("stripe_payments.settings") as mock_settings:
            mock_settings.stripe_secret_key = "sk_test_xxx"
            assert is_configured() is True


class TestInitStripe:
    def test_sets_api_key_when_configured(self):
        with patch("stripe_payments.stripe_lib") as mock_stripe:
            with patch("stripe_payments.settings") as mock_settings:
                mock_settings.stripe_secret_key = "sk_test_xxx"
                init_stripe()
                assert mock_stripe.api_key == "sk_test_xxx"

    def test_does_not_set_when_no_key(self):
        with patch("stripe_payments.stripe_lib") as mock_stripe:
            with patch("stripe_payments.settings") as mock_settings:
                mock_settings.stripe_secret_key = ""
                mock_stripe.api_key = None  # Clear auto-created mock attr
                init_stripe()
                # api_key should remain None since secret key is empty
                assert mock_stripe.api_key is None


class TestCreateCheckoutSession:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self):
        with patch("stripe_payments.is_configured", return_value=False):
            result = await create_checkout_session(
                invoice_id="i1", invoice_number=1,
                customer_id="c1", customer_email="a@b.com",
                amount=100.0, line_items_desc="Test",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_session_data_on_success(self):
        mock_session = MagicMock()
        mock_session.id = "cs_test_xxx"
        mock_session.url = "https://checkout.stripe.com/test"

        with patch("stripe_payments.is_configured", return_value=True):
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                mock_stripe.checkout.Session.create.return_value = mock_session
                result = await create_checkout_session(
                    invoice_id="i1", invoice_number=42,
                    customer_id="c1", customer_email="cust@ex.com",
                    amount=50.99, line_items_desc="Repair service",
                )

        assert result is not None
        assert result["session_id"] == "cs_test_xxx"
        assert result["url"] == "https://checkout.stripe.com/test"

        # Verify Stripe API call
        mock_stripe.checkout.Session.create.assert_called_once()
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs["mode"] == "payment"
        assert call_kwargs["metadata"]["invoice_id"] == "i1"
        assert call_kwargs["line_items"][0]["price_data"]["unit_amount"] == 5099  # cents

    @pytest.mark.asyncio
    async def test_returns_none_on_stripe_error(self):
        with patch("stripe_payments.is_configured", return_value=True):
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                from stripe import StripeError
                mock_stripe.checkout.Session.create.side_effect = StripeError("API Error")
                result = await create_checkout_session(
                    invoice_id="i1", invoice_number=1,
                    customer_id="c1", customer_email="a@b.com",
                    amount=100.0, line_items_desc="Test",
                )
                assert result is None


class TestVerifyWebhook:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_webhook_secret(self):
        with patch("stripe_payments.settings") as mock_settings:
            mock_settings.stripe_webhook_secret = ""
            result = await verify_webhook(b"{}", "sig")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_event_on_success(self):
        mock_event = MagicMock()
        mock_event.to_dict_recursive.return_value = {"type": "payment_intent.succeeded", "id": "evt_1"}

        with patch("stripe_payments.settings") as mock_settings:
            mock_settings.stripe_webhook_secret = "whsec_test"
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                mock_stripe.Webhook.construct_event.return_value = mock_event
                result = await verify_webhook(b'{"test": true}', "sig_header")

        assert result == {"type": "payment_intent.succeeded", "id": "evt_1"}

    @pytest.mark.asyncio
    async def test_returns_none_on_verification_error(self):
        with patch("stripe_payments.settings") as mock_settings:
            mock_settings.stripe_webhook_secret = "whsec_test"
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                from stripe import StripeError
                mock_stripe.Webhook.construct_event.side_effect = StripeError("Bad sig")
                result = await verify_webhook(b"{}", "sig")
                assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_value_error(self):
        with patch("stripe_payments.settings") as mock_settings:
            mock_settings.stripe_webhook_secret = "whsec_test"
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                mock_stripe.Webhook.construct_event.side_effect = ValueError("bad payload")
                result = await verify_webhook(b"{}", "sig")
                assert result is None


class TestCreateSetupIntent:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self):
        with patch("stripe_payments.is_configured", return_value=False):
            result = await create_setup_intent("c1")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_client_secret_on_success(self):
        mock_intent = MagicMock()
        mock_intent.client_secret = "seti_secret_xxx"
        mock_intent.id = "seti_123"

        with patch("stripe_payments.is_configured", return_value=True):
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                mock_stripe.SetupIntent.create.return_value = mock_intent
                result = await create_setup_intent("cust_42")

        assert result["client_secret"] == "seti_secret_xxx"
        assert result["id"] == "seti_123"

    @pytest.mark.asyncio
    async def test_returns_none_on_stripe_error(self):
        with patch("stripe_payments.is_configured", return_value=True):
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                from stripe import StripeError
                mock_stripe.SetupIntent.create.side_effect = StripeError("fail")
                result = await create_setup_intent("c1")
                assert result is None


class TestCreatePaymentIntent:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self):
        with patch("stripe_payments.is_configured", return_value=False):
            result = await create_payment_intent(
                invoice_id="i1", invoice_number=1,
                customer_email="a@b.com", amount=50.0,
                payment_method_id="pm_123",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_intent_data_on_success(self):
        mock_intent = MagicMock()
        mock_intent.id = "pi_test_xxx"
        mock_intent.status = "succeeded"

        with patch("stripe_payments.is_configured", return_value=True):
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                mock_stripe.PaymentIntent.create.return_value = mock_intent
                result = await create_payment_intent(
                    invoice_id="i1", invoice_number=42,
                    customer_email="cust@ex.com", amount=99.99,
                    payment_method_id="pm_xxx",
                )

        assert result["payment_intent_id"] == "pi_test_xxx"
        assert result["status"] == "succeeded"
        assert result["amount"] == 99.99

        mock_stripe.PaymentIntent.create.assert_called_once()
        call_kwargs = mock_stripe.PaymentIntent.create.call_args[1]
        assert call_kwargs["amount"] == 9999  # cents
        assert call_kwargs["confirm"] is True
        assert call_kwargs["off_session"] is True

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_stripe_error(self):
        with patch("stripe_payments.is_configured", return_value=True):
            with patch("stripe_payments.stripe_lib") as mock_stripe:
                from stripe import StripeError
                mock_stripe.PaymentIntent.create.side_effect = StripeError("fail")
                result = await create_payment_intent(
                    invoice_id="i1", invoice_number=1,
                    customer_email="a@b.com", amount=10.0,
                    payment_method_id="pm_1",
                )
                assert result == {}
