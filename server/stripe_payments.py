"""Stripe payment processing for SpacetimeCRM."""

import logging
from typing import Any, Optional

import stripe as stripe_lib
from stripe import StripeError

from config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """Check if Stripe is configured with a secret key."""
    return bool(settings.stripe_secret_key)


def init_stripe() -> None:
    """Initialize the Stripe client with the configured API key."""
    if settings.stripe_secret_key:
        stripe_lib.api_key = settings.stripe_secret_key


async def create_checkout_session(
    invoice_id: str,
    invoice_number: int,
    customer_id: str,
    customer_email: str,
    amount: float,
    line_items_desc: str,
) -> Optional[dict[str, Any]]:
    """Create a Stripe Checkout Session for an invoice payment.

    Returns dict with session_id and url, or None if Stripe isn't configured.
    """
    if not is_configured():
        logger.warning("Stripe not configured — skipping checkout session creation")
        return None

    init_stripe()

    try:
        session = stripe_lib.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=customer_email,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Invoice #{invoice_number}",
                            "description": line_items_desc or f"Payment for Invoice #{invoice_number}",
                        },
                        "unit_amount": int(round(amount * 100)),  # cents
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "invoice_id": invoice_id,
                "customer_id": customer_id,
                "invoice_number": str(invoice_number),
            },
            success_url=f"{settings.app_url}/portal/invoices?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app_url}/portal/invoices",
        )
        logger.info("Stripe checkout session created: %s", session.id)
        return {"session_id": session.id, "url": session.url}
    except StripeError as e:
        logger.error("Stripe checkout session failed: %s", e)
        return None


async def verify_webhook(payload: bytes, sig_header: str) -> Optional[dict[str, Any]]:
    """Verify and parse a Stripe webhook event.

    Returns the event dict on success, or None if verification fails.
    """
    if not settings.stripe_webhook_secret:
        logger.warning("Stripe webhook secret not configured — skipping webhook verification")
        return None

    init_stripe()

    try:
        event = stripe_lib.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
        return event.to_dict_recursive()
    except StripeError as e:
        logger.error("Stripe webhook signature verification failed: %s", e)
        return None
    except ValueError as e:
        logger.error("Stripe webhook payload error: %s", e)
        return None


async def create_setup_intent(customer_id: str) -> Optional[dict[str, Any]]:
    """Create a Stripe SetupIntent to securely collect a payment method.

    Returns dict with client_secret, or None if Stripe isn't configured.
    """
    if not is_configured():
        logger.warning("Stripe not configured — skipping setup intent")
        return None

    init_stripe()

    try:
        intent = stripe_lib.SetupIntent.create(
            payment_method_types=["card"],
            metadata={"customer_id": customer_id},
        )
        logger.info("Stripe SetupIntent created for customer %s", customer_id)
        return {"client_secret": intent.client_secret, "id": intent.id}
    except StripeError as e:
        logger.error("Stripe SetupIntent failed: %s", e)
        return None


async def create_payment_intent(
    invoice_id: str,
    invoice_number: int,
    customer_email: str,
    amount: float,
    payment_method_id: str,
) -> Optional[dict[str, Any]]:
    """Create and confirm a Stripe PaymentIntent using a saved payment method.

    Returns dict with status + payment_intent_id, or None on failure.
    """
    if not is_configured():
        logger.warning("Stripe not configured — skipping payment intent")
        return None

    init_stripe()

    try:
        intent = stripe_lib.PaymentIntent.create(
            amount=int(round(amount * 100)),
            currency="usd",
            payment_method=payment_method_id,
            receipt_email=customer_email,
            off_session=True,
            confirm=True,
            metadata={
                "invoice_id": invoice_id,
                "invoice_number": str(invoice_number),
            },
        )
        logger.info(
            "Stripe PaymentIntent %s: status=%s for invoice #%s",
            intent.id,
            intent.status,
            invoice_number,
        )
        return {
            "payment_intent_id": intent.id,
            "status": intent.status,
            "amount": amount,
        }
    except StripeError as e:
        logger.error("Stripe PaymentIntent failed: %s", e)
        return {}
