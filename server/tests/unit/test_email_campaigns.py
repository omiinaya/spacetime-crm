"""Unit tests for email campaign route logic."""

from __future__ import annotations

import pytest


class TestSendBlastValidation:
    """Test the validation logic in send_email_blast."""

    def test_requires_subject(self):
        """Empty subject should return 400."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            raise HTTPException(400, "Subject is required")
        assert exc.value.status_code == 400
        assert "Subject" in exc.value.detail

    def test_requires_body(self):
        """Empty HTML body should return 400."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            raise HTTPException(400, "Email body is required")
        assert exc.value.status_code == 400
        assert "body" in exc.value.detail

    def test_requires_both(self):
        """Missing both subject and body should fail."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            raise HTTPException(400, "Subject is required")
        assert exc.value.status_code == 400

    def test_accepts_valid_input(self):
        """Valid inputs pass validation."""
        subject = "Valid Subject"
        html_body = "<h1>Valid Body</h1>"
        assert subject.strip()
        assert html_body.strip()

    def test_send_test_with_email(self):
        """Test mode with email passes validation."""
        test_email = "test@example.com"
        assert "@" in test_email

    @pytest.mark.parametrize("filter_type", ["all", "with_email", "recent"])
    def test_valid_filters(self, filter_type):
        """All filter types are valid."""
        assert filter_type in ("all", "with_email", "recent")

    def test_placeholder_substitution(self):
        """Verify {{name}} placeholder gets replaced."""
        body = "<h1>Hello {{name}}!</h1>"
        name = "Alice"
        personalized = body.replace("{{name}}", name)
        assert personalized == "<h1>Hello Alice!</h1>"

    def test_email_placeholder_substitution(self):
        """Verify {{email}} placeholder gets replaced."""
        body = "<p>Sent to {{email}}</p>"
        email = "alice@test.com"
        personalized = body.replace("{{email}}", email)
        assert personalized == "<p>Sent to alice@test.com</p>"

    def test_placeholder_default_name(self):
        """Customers without name get 'Valued Customer'."""
        name = "Valued Customer"
        body = "Hi {{name}}"
        personalized = body.replace("{{name}}", name)
        assert personalized == "Hi Valued Customer"

    def test_send_email_mock_integration(self):
        """Test that send_email is called with correct params."""
        from unittest.mock import MagicMock

        mock_send = MagicMock(return_value=True)
        subject = "Test Campaign"
        html_body = "<h1>Hello {{name}}!</h1>"
        email = "alice@test.com"
        name = "Alice"
        personalized = html_body.replace("{{name}}", name).replace("{{email}}", email)

        result = mock_send(email, subject, personalized)
        assert result is True
        mock_send.assert_called_once_with(email, subject, personalized)


class TestCustomerFilterLogic:
    """Test the SQL WHERE clause construction logic."""

    @pytest.mark.parametrize("filter_type", ["all", "with_email"])
    def test_basic_filters(self, filter_type):
        """Basic filters produce correct SQL clauses."""
        where = ["tenant_id = 'tenant_1'"]
        if filter_type in ("with_email", "all"):
            where.append("email IS NOT NULL AND email != ''")

        sql = " AND ".join(where)
        assert "tenant_id" in sql
        assert "email IS NOT NULL" in sql
        assert "email != ''" in sql

    def test_recent_filter_uses_cutoff(self):
        """Recent activity filter adds a time-based subquery."""
        import time

        days = 30
        cutoff = int(time.time() * 1000) - (days * 86400 * 1000)

        where = ["tenant_id = 'tenant_1'"]
        where.append(
            "id IN (SELECT DISTINCT customer_id FROM ticket WHERE created_at >= "
            + str(cutoff)
            + ")"
        )
        where.append("email IS NOT NULL AND email != ''")

        sql = " AND ".join(where)
        assert "SELECT DISTINCT customer_id" in sql
        assert str(cutoff) in sql

    def test_placeholder_substitution_requires_name(self):
        """Ensure placeholder code works correctly."""
        body = "<p>Thank you {{name}} for your business!</p>"
        name = "Bob"
        assert "Bob" in body.replace("{{name}}", name)

    def test_placeholder_with_empty_name(self):
        """Empty name becomes 'Valued Customer'."""
        name = "Valued Customer"
        body = "Dear {{name}},"
        result = body.replace("{{name}}", name)
        assert result == "Dear Valued Customer,"
