"""The models override BaseModel = SanitizedModel for auto HTML stripping.

String fields should have HTML tags stripped after validation.
Fields named 'password', 'token', 'secret', 'smtp_password', and
'twilio_auth_token' must be skipped to preserve opaque values.
"""

from __future__ import annotations


class TestSanitizedModel:
    def test_strips_html_from_regular_fields(self) -> None:
        from models import CustomerCreate

        m = CustomerCreate(
            first_name="<script>alert('xss')</script>Alice",
            last_name="<b>Smith</b>",
            company='<a href="evil">Acme</a>',
        )
        assert m.first_name == "alert('xss')Alice"
        assert m.last_name == "Smith"
        assert m.company == "Acme"

    def test_skips_password_field(self) -> None:
        from models import LoginRequest

        m = LoginRequest(
            email="user@example.com",
            password="<secret>abc123</secret>",
        )
        # password field is in _SKIP_SANITIZE — tags preserved
        assert m.password == "<secret>abc123</secret>"

    def test_skips_token_field(self) -> None:
        from models import ResetPasswordRequest

        m = ResetPasswordRequest(
            password="newpass123",
            token="<reset-token-abc>",
        )
        assert m.token == "<reset-token-abc>"

    def test_skips_secret_field(self) -> None:
        from models import WebhookSubscriptionCreate

        m = WebhookSubscriptionCreate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
            secret="<hmac-secret>",
        )
        assert m.secret == "<hmac-secret>"

    def test_strips_html_from_email_field(self) -> None:
        from models import LoginRequest

        m = LoginRequest(
            email="  user@example.com  ",
            password="validpw",
        )
        # SanitizedModel strips HTML even from email
        assert m.email == "  user@example.com  "  # no tags, no change
        # Also test with tags
        m2 = LoginRequest(email="<b>user@example.com</b>", password="validpw")
        assert m2.email == "user@example.com"

    def test_nested_model_html_stripping(self) -> None:
        """Verify HTML stripping works on nested Pydantic models."""
        from models import RecurringInvoiceLineItem, RecurringInvoiceRuleCreate

        item = RecurringInvoiceLineItem(
            description="<script>alert(1)</script>Laptop repair",
            quantity=1,
            unit_price=99.99,
        )
        assert item.description == "alert(1)Laptop repair"

        rule = RecurringInvoiceRuleCreate(
            customer_id="c-001",
            name="<em>Monthly Invoice</em>",
            frequency="monthly",
            line_items=[item],
        )
        assert rule.name == "Monthly Invoice"

    def test_strips_html_from_mail_settings(self) -> None:
        """smtp_password is in _SKIP_SANITIZE but other fields should be stripped."""
        from models import MailSettingsUpdate

        m = MailSettingsUpdate(
            smtp_host="<b>smtp.example.com</b>",
            smtp_port=587,
            smtp_user="<i>bot@example.com</i>",
            smtp_password="<super-secret>",
            smtp_from_email="noreply@example.com",
        )
        assert m.smtp_host == "smtp.example.com"
        assert m.smtp_user == "bot@example.com"
        # smtp_password is in _SKIP_SANITIZE
        assert m.smtp_password == "<super-secret>"
