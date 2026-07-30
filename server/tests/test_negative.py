"""Negative and boundary API integration tests.

Tests verify correct HTTP status codes for:
  - Invalid/missing request bodies (422)
  - Missing required fields (422)
  - Non-existent resources (404)
  - Unauthenticated requests (401)
  - Invalid enum values (accepted per model definition)
"""

import httpx

from .conftest import SERVER_URL, unique_suffix


class TestCustomerValidation:
    """Customer creation validation (422)."""

    def test_create_customer_empty_name(self, test_admin_headers: dict):
        """POST /api/customers with empty first_name returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/customers",
            json={
                "first_name": "",  # min_length=1 fails
                "last_name": "Doe",
                "email": "empty-first@test.com",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for empty first_name, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )

    def test_create_customer_missing_required(self, test_admin_headers: dict):
        """POST /api/customers with empty body returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/customers",
            json={},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for missing required fields, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )


class TestInvoiceValidation:
    """Invoice creation validation (422)."""

    def test_create_invoice_missing_customer(self, test_admin_headers: dict):
        """POST /api/invoices without customer_id returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices",
            json={
                "notes": "Invoice with no customer",
                "terms": "Net 30",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for missing customer_id, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )


class TestNotFound:
    """Non-existent resource access (404)."""

    def test_get_nonexistent_invoice_pdf(self, test_admin_headers: dict):
        """GET /api/invoices/{nonexistent_id}/pdf returns 404.

        The API has no GET /api/tickets/{id} endpoint; /api/invoices/{id}/pdf is
        the closest GET endpoint that explicitly returns 404 for missing resources.
        """
        fid = f"nonexistent-{unique_suffix()}"
        resp = httpx.get(
            f"{SERVER_URL}/api/invoices/{fid}/pdf",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for nonexistent invoice PDF, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )


class TestAuthentication:
    """Unauthenticated access (401)."""

    def test_unauthenticated_access(self):
        """GET /api/customers without auth header returns 401."""
        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            timeout=10,
        )
        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated request, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )


class TestTicketBoundary:
    """Ticket creation with boundary/invalid values."""

    def test_create_ticket_invalid_priority(
        self, test_admin_headers: dict, session_suffix: str
    ):
        """POST /api/tickets with invalid priority is accepted (model has no enum validation).

        The TicketCreate model defines priority as a plain str with no enum
        constraint, so any string is accepted.
        """
        from .conftest import create_customer

        customer = create_customer(
            test_admin_headers,
            session_suffix=session_suffix,
            first_name="Boundary",
            last_name="Test",
        )
        cid = customer.get("id")
        assert cid, f"Failed to create customer: {customer}"

        suf = unique_suffix()
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets",
            json={
                "customer_id": cid,
                "title": "Invalid priority test",
                "description": "Testing with an invalid priority value",
                "device_type": "Phone",
                "device_serial": f"INVALID-PRIORITY-{session_suffix}-{suf}",
                "priority": "invalid_priority_value",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        # The model accepts any string for priority, so we expect 200 (not 422 or 500).
        assert resp.status_code == 200, (
            f"Expected 200 (no enum validation on priority), "
            f"got {resp.status_code}: {resp.text[:200]}"
        )
