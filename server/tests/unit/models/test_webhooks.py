"""Webhook models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestWebhookSubscriptionCreate:
    def test_valid(self) -> None:
        from models import WebhookSubscriptionCreate

        m = WebhookSubscriptionCreate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
        )
        assert m.url == "https://hooks.example.com/callback"
        assert m.events == "ticket.created"

    def test_url_too_short(self) -> None:
        """min_length=5."""
        from models import WebhookSubscriptionCreate

        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(url="http", events="e")

    def test_url_too_long(self) -> None:
        from models import WebhookSubscriptionCreate

        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(url="x" * 2001, events="e")

    def test_events_empty_raises(self) -> None:
        from models import WebhookSubscriptionCreate

        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(url="https://example.com/hook", events="")
