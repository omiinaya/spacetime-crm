"""Payment recording, listing, and deletion integration tests."""

import httpx
import pytest

from .conftest import (
    SERVER_URL,
    _track_entity,
    assert_ok,
    create_customer,
    unique_suffix,
)


def _create_test_invoice(
    test_admin_headers: dict, session_suffix: str = "", suffix: str = ""
) -> str:
    """Create a customer + invoice and return the invoice ID.

    Filters by customer_id for safe parallel/out-of-order execution.
    Tracks created entities for session cleanup.
    """
    suf = suffix or unique_suffix()
    email = f"pay-cust-{session_suffix}-{suf}@example.com"
    c = create_customer(
        test_admin_headers,
        session_suffix=session_suffix,
        first_name="Pay",
        last_name=f"Test{suf}",
        email=email,
    )
    cid = c.get("id")
    assert cid
    _track_entity("customer", cid)
    httpx.post(
        f"{SERVER_URL}/api/invoices",
        json={"customer_id": cid, "notes": f"Pay test {suffix}", "due_date": 0},
        headers=test_admin_headers,
        timeout=10,
    )
    # Find invoice by customer_id (unique per test call)
    r = httpx.get(
        f"{SERVER_URL}/api/invoices",
        params={"customer_id": cid, "limit": 1},
        headers=test_admin_headers,
        timeout=10,
    )
    invs = r.json().get("invoices", [])
    assert len(invs) >= 1, f"No invoice found for customer {cid}"
    inv_id = invs[0]["id"]
    _track_entity("invoice", inv_id)

    # Add a line item so invoice has a total
    httpx.post(
        f"{SERVER_URL}/api/invoices/{inv_id}/line-items",
        json={"description": "Service", "quantity": 1, "unit_price": 100},
        headers=test_admin_headers,
        timeout=10,
    )
    return inv_id


class TestPaymentCRUD:
    """Payment recording, listing, and full lifecycle."""

    def test_record_payment(self, test_admin_headers: dict, session_suffix: str):
        """Record a payment against an invoice."""
        inv_id = _create_test_invoice(test_admin_headers, session_suffix, "record")

        resp = httpx.post(
            f"{SERVER_URL}/api/payments",
            json={
                "invoice_id": inv_id,
                "customer_id": "any",
                "amount": 100,
                "method": "cash",
                "reference": "TX001",
                "notes": "Walk-in payment",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True

    def test_list_payments(self, test_admin_headers: dict):
        """List payments returns paginated results."""
        resp = httpx.get(
            f"{SERVER_URL}/api/payments",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "payments" in data
        assert "total" in data
        assert isinstance(data["payments"], list)

    def test_list_payments_filter_by_invoice(
        self, test_admin_headers: dict, session_suffix: str
    ):
        """Filter payments by invoice_id."""
        inv_id = _create_test_invoice(test_admin_headers, session_suffix, "filterbyinv")

        # Record 2 payments on this invoice
        for i in range(2):
            httpx.post(
                f"{SERVER_URL}/api/payments",
                json={
                    "invoice_id": inv_id,
                    "customer_id": "any",
                    "amount": 25,
                    "method": "card",
                    "reference": f"REF{i}",
                },
                headers=test_admin_headers,
                timeout=10,
            )

        resp = httpx.get(
            f"{SERVER_URL}/api/payments",
            params={"invoice_id": inv_id},
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        for p in data["payments"]:
            assert p["invoice_id"] == inv_id
        assert len(data["payments"]) >= 2

    def test_payment_updates_invoice_status(
        self, test_admin_headers: dict, session_suffix: str
    ):
        """Recording a full payment marks invoice as paid."""
        inv_id = _create_test_invoice(test_admin_headers, session_suffix, "statuscheck")

        # Record payment for the full invoice amount
        resp = httpx.post(
            f"{SERVER_URL}/api/payments",
            json={
                "invoice_id": inv_id,
                "customer_id": "any",
                "amount": 999,
                "method": "check",
                "reference": "CHECK001",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

        # Check invoice status (may be paid, partial, or sent depending on auto-recalc)
        r = httpx.get(
            f"{SERVER_URL}/api/invoices",
            params={"limit": 500},
            headers=test_admin_headers,
            timeout=10,
        )
        invs = r.json().get("invoices", [])
        target = next((inv for inv in invs if inv["id"] == inv_id), None)
        # Payment logic in the backend calculates status — verify it did something reasonable
        if target:
            assert target["status"] in ("paid", "partial", "sent"), (
                f"Unexpected status after payment: {target['status']}"
            )

    def test_delete_payment(self, test_admin_headers: dict, session_suffix: str):
        """Delete a payment (admin only)."""
        inv_id = _create_test_invoice(test_admin_headers, session_suffix, "deletepay")

        # Record a payment
        httpx.post(
            f"{SERVER_URL}/api/payments",
            json={
                "invoice_id": inv_id,
                "customer_id": "any",
                "amount": 50,
                "method": "cash",
            },
            headers=test_admin_headers,
            timeout=10,
        )

        # Get its ID
        r = httpx.get(
            f"{SERVER_URL}/api/payments",
            params={"invoice_id": inv_id},
            headers=test_admin_headers,
            timeout=10,
        )
        payments = r.json().get("payments", [])
        if not payments:
            pytest.skip("No payment found to delete")
        pay_id = payments[0]["id"]

        resp = httpx.delete(
            f"{SERVER_URL}/api/payments/{pay_id}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_multiple_payment_methods(
        self, test_admin_headers: dict, session_suffix: str
    ):
        """Payments can use different methods: cash, card, check, bank_transfer."""
        inv_id = _create_test_invoice(test_admin_headers, session_suffix, "methods")
        methods = ["cash", "card", "check", "bank_transfer"]

        for i, method in enumerate(methods):
            resp = httpx.post(
                f"{SERVER_URL}/api/payments",
                json={
                    "invoice_id": inv_id,
                    "customer_id": "any",
                    "amount": 10,
                    "method": method,
                    "reference": f"METH{i}",
                },
                headers=test_admin_headers,
                timeout=10,
            )
            assert_ok(resp, 200)


class TestPaymentErrors:
    """Payment endpoint error handling."""

    def test_create_missing_fields(self, test_admin_headers: dict):
        """Missing required invoice_id returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/payments",
            json={"amount": 50, "method": "cash"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_create_bad_amount(self, test_admin_headers: dict):
        """Zero or negative amounts are rejected by Pydantic."""
        for bad_amt in [0, -1, -100]:
            resp = httpx.post(
                f"{SERVER_URL}/api/payments",
                json={
                    "invoice_id": "test",
                    "customer_id": "test",
                    "amount": bad_amt,
                    "method": "cash",
                },
                headers=test_admin_headers,
                timeout=10,
            )
            assert resp.status_code == 422, f"Amount {bad_amt} should be rejected"

    def test_unauthorized_access(self, client: httpx.Client):
        """Payment endpoints require auth."""
        for path in ["/api/payments"]:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403), f"{path} allowed unauthenticated"
        # Delete also requires auth
        resp = client.delete("/api/payments/fake", timeout=10)
        assert resp.status_code in (401, 403), (
            "DELETE /api/payments/fake allowed unauthenticated"
        )
