"""Unit tests for server/stripe_payments.py.

Tests Stripe configuration checking, checkout session creation,
webhook verification, setup intents, and payment intents.
All Stripe calls are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _patch_settings():
    """Provide a clean settings mock for each test."""
    with patch("stripe_payments.settings") as mock_settings:
        mock_settings.stripe_secret_key = ""
        mock_settings.stripe_webhook_secret = ""
        mock_settings.app_url = "http://localhost:8723"
        yield mock_settings


@pytest.fixture
def _configured_settings():
    """Return a settings patch with valid keys."""
    with patch("stripe_payments.settings") as mock_settings:
        mock_settings.stripe_secret_key = "sk_test_123456789"
        mock_settings.stripe_webhook_secret = "whsec_testsecret"
        mock_settings.app_url = "http://localhost:8723"
        yield mock_settings


class TestIsConfigured:
    """Stripe configuration detection."""

    def test_returns_false_when_no_key(self) -> None:
        from stripe_payments import is_configured

        assert is_configured() is False

    def test_returns_true_when_key_present(self, _configured_settings) -> None:
        from stripe_payments import is_configured

        assert is_configured() is True

    def test_returns_false_when_key_empty_string(self) -> None:
        """Empty string should not count as configured."""
        from stripe_payments import is_configured

        assert is_configured() is False


class TestInitStripe:
    """Stripe client initialization."""

    def test_sets_api_key_when_configured(self, _configured_settings) -> None:
        """Should set stripe_lib.api_key when secret key is present."""
        import stripe_payments
        import stripe as stripe_lib

        with patch.object(stripe_lib, "api_key", ""):
            stripe_payments.init_stripe()
            assert stripe_lib.api_key == "sk_test_123456789"

    def test_does_not_set_api_key_when_not_configured(self) -> None:
        """Should not set api_key when no secret key."""
        import stripe_payments
        import stripe as stripe_lib

        original = stripe_lib.api_key
        stripe_payments.init_stripe()
        assert stripe_lib.api_key == original


class TestCreateCheckoutSession:
    """Stripe Checkout Session creation."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self) -> None:
        """Should return None when Stripe is not configured."""
        from stripe_payments import create_checkout_session

        result = await create_checkout_session(
            invoice_id="inv-1", invoice_number=100,
            customer_id="cust-1", customer_email="test@test.com",
            amount=50.0, line_items_desc="Test invoice",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_creates_session_successfully(self, _configured_settings) -> None:
        """Should return session_id and url on success."""
        import stripe as stripe_lib

        mock_session = MagicMock()
        mock_session.id = "cs_test_abc123"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc123"

        with patch.object(stripe_lib.checkout, "Session") as mock_session_class:
            mock_session_class.create.return_value = mock_session
            with patch("stripe_payments.logger"):
                from stripe_payments import create_checkout_session

                result = await create_checkout_session(
                    invoice_id="inv-1", invoice_number=100,
                    customer_id="cust-1", customer_email="test@test.com",
                    amount=50.0, line_items_desc="Invoice for May",
                )

        assert result == {
            "session_id": "cs_test_abc123",
            "url": "https://checkout.stripe.com/pay/cs_test_abc123",
        }

    @pytest.mark.asyncio
    async def test_passes_correct_amount_in_cents(self, _configured_settings) -> None:
        """Should convert dollars to cents."""
        import stripe as stripe_lib

        mock_session = MagicMock()
        mock_session.id = "cs_test_1"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_1"

        with patch.object(stripe_lib.checkout, "Session") as mock_session_class:
            mock_session_class.create.return_value = mock_session
            with patch("stripe_payments.logger"):
                from stripe_payments import create_checkout_session

                await create_checkout_session(
                    invoice_id="inv-1", invoice_number=100,
                    customer_id="cust-1", customer_email="test@test.com",
                    amount=99.99, line_items_desc="",
                )

        call_kwargs = mock_session_class.create.call_args[1]
        assert call_kwargs["line_items"][0]["price_data"]["unit_amount"] == 9999  # $99.99 in cents
        assert call_kwargs["metadata"]["invoice_id"] == "inv-1"
        assert call_kwargs["metadata"]["customer_id"] == "cust-1"

    @pytest.mark.asyncio
    async def test_sets_correct_urls(self, _configured_settings) -> None:
        """Should use app_url for success and cancel URLs."""
        import stripe as stripe_lib

        mock_session = MagicMock()
        mock_session.id = "cs_test_2"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_2"

        with patch.object(stripe_lib.checkout, "Session") as mock_session_class:
            mock_session_class.create.return_value = mock_session
            with patch("stripe_payments.logger"):
                from stripe_payments import create_checkout_session

                await create_checkout_session(
                    invoice_id="inv-2", invoice_number=101,
                    customer_id="cust-2", customer_email="a@b.com",
                    amount=25.0, line_items_desc="Desc",
                )

        call_kwargs = mock_session_class.create.call_args[1]
        assert "http://localhost:8723/portal/invoices?session_id={CHECKOUT_SESSION_ID}" in call_kwargs["success_url"]
        assert "http://localhost:8723/portal/invoices" in call_kwargs["cancel_url"]

    @pytest.mark.asyncio
    async def test_handles_stripe_error(self, _configured_settings) -> None:
        """Should return None when Stripe raises an error."""
        import stripe as stripe_lib
        from stripe import StripeError

        with patch.object(stripe_lib.checkout, "Session") as mock_session_class:
            mock_session_class.create.side_effect = StripeError("API error")
            with patch("stripe_payments.logger") as mock_logger:
                from stripe_payments import create_checkout_session

                result = await create_checkout_session(
                    invoice_id="inv-3", invoice_number=102,
                    customer_id="cust-3", customer_email="a@b.com",
                    amount=10.0, line_items_desc="",
                )

        assert result is None
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handles_empty_line_items_desc(self, _configured_settings) -> None:
        """Should use default description when line_items_desc is empty."""
        import stripe as stripe_lib

        mock_session = MagicMock()
        mock_session.id = "cs_test_3"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_3"

        with patch.object(stripe_lib.checkout, "Session") as mock_session_class:
            mock_session_class.create.return_value = mock_session
            with patch("stripe_payments.logger"):
                from stripe_payments import create_checkout_session

                await create_checkout_session(
                    invoice_id="inv-4", invoice_number=200,
                    customer_id="cust-4", customer_email="a@b.com",
                    amount=10.0, line_items_desc="",
                )

        call_kwargs = mock_session_class.create.call_args[1]
        desc = call_kwargs["line_items"][0]["price_data"]["product_data"]["description"]
        assert "Invoice #200" in desc


class TestVerifyWebhook:
    """Stripe webhook signature verification."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_webhook_secret(self) -> None:
        """Should return None when webhook secret is not configured."""
        from stripe_payments import verify_webhook

        result = await verify_webhook(b"{}", "tsec_123")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_event_on_success(self, _configured_settings) -> None:
        """Should return event dict on successful verification."""
        import stripe as stripe_lib

        mock_event = MagicMock()
        mock_event.to_dict_recursive.return_value = {
            "id": "evt_123",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_456"}},
        }

        with patch.object(stripe_lib.Webhook, "construct_event", return_value=mock_event):
            from stripe_payments import verify_webhook

            result = await verify_webhook(b'{"test": true}', "tsec_abc")

        assert result == {
            "id": "evt_123",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_456"}},
        }

    @pytest.mark.asyncio
    async def test_handles_stripe_error(self, _configured_settings) -> None:
        """Should return None when StripeError occurs during verification."""
        import stripe as stripe_lib
        from stripe import StripeError

        with patch.object(stripe_lib.Webhook, "construct_event", side_effect=StripeError("Invalid signature")):
            with patch("stripe_payments.logger") as mock_logger:
                from stripe_payments import verify_webhook

                result = await verify_webhook(b"{}", "tsec_bad")

        assert result is None
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handles_value_error(self, _configured_settings) -> None:
        """Should return None when ValueError occurs (invalid payload)."""
        import stripe as stripe_lib

        with patch.object(stripe_lib.Webhook, "construct_event", side_effect=ValueError("Invalid payload")):
            with patch("stripe_payments.logger") as mock_logger:
                from stripe_payments import verify_webhook

                result = await verify_webhook(b"bad data", "tsec_bad")

        assert result is None
        mock_logger.error.assert_called()


class TestCreateSetupIntent:
    """Stripe SetupIntent creation."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self) -> None:
        """Should return None when Stripe is not configured."""
        from stripe_payments import create_setup_intent

        result = await create_setup_intent("cust-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_creates_setup_intent_successfully(self, _configured_settings) -> None:
        """Should return client_secret and id on success."""
        mock_intent = MagicMock()
        mock_intent.client_secret = "seti_1_secret_abc"
        mock_intent.id = "seti_1"

        with patch("stripe_payments.stripe_lib.SetupIntent.create", return_value=mock_intent):
            with patch("stripe_payments.logger"):
                from stripe_payments import create_setup_intent

                result = await create_setup_intent("cust-123")

        assert result == {"client_secret": "seti_1_secret_abc", "id": "seti_1"}

    @pytest.mark.asyncio
    async def test_passes_customer_id_in_metadata(self, _configured_settings) -> None:
        """Should include customer_id in metadata."""
        mock_intent = MagicMock()
        mock_intent.client_secret = "secret_xyz"
        mock_intent.id = "seti_2"

        mock_create = MagicMock(return_value=mock_intent)
        with patch("stripe_payments.stripe_lib.SetupIntent.create", mock_create):
            with patch("stripe_payments.logger"):
                from stripe_payments import create_setup_intent

                await create_setup_intent("cust-456")

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["metadata"]["customer_id"] == "cust-456"
        assert call_kwargs["payment_method_types"] == ["card"]

    @pytest.mark.asyncio
    async def test_handles_stripe_error(self, _configured_settings) -> None:
        """Should return None when StripeError occurs."""
        from stripe import StripeError

        with patch("stripe_payments.stripe_lib.SetupIntent.create", side_effect=StripeError("Setup failed")):
            with patch("stripe_payments.logger") as mock_logger:
                from stripe_payments import create_setup_intent

                result = await create_setup_intent("cust-789")

        assert result is None
        mock_logger.error.assert_called()


class TestCreatePaymentIntent:
    """Stripe PaymentIntent creation and confirmation."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self) -> None:
        """Should return None when Stripe is not configured."""
        from stripe_payments import create_payment_intent

        result = await create_payment_intent(
            invoice_id="inv-1", invoice_number=100,
            customer_email="a@b.com", amount=50.0,
            payment_method_id="pm_123",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_creates_payment_intent_successfully(self, _configured_settings) -> None:
        """Should return payment_intent_id and status on success."""
        mock_intent = MagicMock()
        mock_intent.id = "pi_abc123"
        mock_intent.status = "succeeded"

        with patch("stripe_payments.stripe_lib.PaymentIntent.create", return_value=mock_intent):
            with patch("stripe_payments.logger"):
                from stripe_payments import create_payment_intent

                result = await create_payment_intent(
                    invoice_id="inv-1", invoice_number=100,
                    customer_email="a@b.com", amount=50.0,
                    payment_method_id="pm_123",
                )

        assert result == {
            "payment_intent_id": "pi_abc123",
            "status": "succeeded",
            "amount": 50.0,
        }

    @pytest.mark.asyncio
    async def test_passes_correct_params(self, _configured_settings) -> None:
        """Should pass amount in cents and metadata."""
        mock_intent = MagicMock()
        mock_intent.id = "pi_xyz"
        mock_intent.status = "requires_confirmation"

        mock_create = MagicMock(return_value=mock_intent)
        with patch("stripe_payments.stripe_lib.PaymentIntent.create", mock_create):
            with patch("stripe_payments.logger"):
                from stripe_payments import create_payment_intent

                await create_payment_intent(
                    invoice_id="inv-2", invoice_number=200,
                    customer_email="cust@test.com", amount=99.99,
                    payment_method_id="pm_456",
                )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["amount"] == 9999  # $99.99 in cents
        assert call_kwargs["currency"] == "usd"
        assert call_kwargs["payment_method"] == "pm_456"
        assert call_kwargs["receipt_email"] == "cust@test.com"
        assert call_kwargs["off_session"] is True
        assert call_kwargs["confirm"] is True
        assert call_kwargs["metadata"]["invoice_id"] == "inv-2"
        assert call_kwargs["metadata"]["invoice_number"] == "200"

    @pytest.mark.asyncio
    async def test_handles_stripe_error(self, _configured_settings) -> None:
        """Should return empty dict when StripeError occurs."""
        from stripe import StripeError

        with patch("stripe_payments.stripe_lib.PaymentIntent.create", side_effect=StripeError("Card declined")):
            with patch("stripe_payments.logger") as mock_logger:
                from stripe_payments import create_payment_intent

                result = await create_payment_intent(
                    invoice_id="inv-1", invoice_number=100,
                    customer_email="a@b.com", amount=50.0,
                    payment_method_id="pm_bad",
                )

        assert result == {}  # Returns empty dict on error
        mock_logger.error.assert_called()
