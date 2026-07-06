"""Invoice CRUD, line items, tax, PDF, and status workflow integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer, unique_suffix


def _create_test_customer(auth_headers: dict, suffix: str = "") -> str:
    """Create a customer and return their ID."""
    suf = suffix or unique_suffix()
    email = f"inv-cust-{suf}@example.com"
    c = create_customer(auth_headers, first_name="Invoice", last_name=f"Test{suf}", email=email)
    cid = c.get("id")
    assert cid, f"Failed to create customer: {c}"
    return cid


def _create_invoice(auth_headers: dict, suffix: str = "", **overrides) -> str:
    """Create a customer + invoice and return the invoice ID.

    Filters by customer_id which is unique per test call,
    so this is safe for parallel or out-of-order execution.
    """
    cid = _create_test_customer(auth_headers, suffix)
    resp = httpx.post(
        f"{SERVER_URL}/api/invoices",
        json={"customer_id": cid, "ticket_id": "", "notes": overrides.get("notes", f"Invoice {suffix}"), "terms": "Net 30", "due_date": overrides.get("due_date", 0)},
        headers=auth_headers, timeout=10,
    )
    assert_ok(resp)

    # Find invoice by customer_id (unique to this test call)
    r = httpx.get(f"{SERVER_URL}/api/invoices", params={"customer_id": cid, "limit": 1}, headers=auth_headers, timeout=10)
    invs = r.json().get("invoices", [])
    assert len(invs) >= 1, f"No invoice found for customer {cid}"
    return invs[0]["id"], cid


class TestInvoiceCRUD:
    """Full invoice lifecycle: create, list, line items, tax, status workflow."""

    def test_create_invoice(self, auth_headers: dict):
        """Create a basic invoice."""
        cid = _create_test_customer(auth_headers, "create")
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices",
            json={"customer_id": cid, "ticket_id": "", "notes": "Test invoice", "terms": "Net 30", "due_date": 0},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_invoices(self, auth_headers: dict):
        """List invoices returns paginated results."""
        resp = httpx.get(
            f"{SERVER_URL}/api/invoices",
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert "invoices" in data
        assert "total" in data
        assert isinstance(data["invoices"], list)

    def test_list_invoices_filter_by_status(self, auth_headers: dict):
        """Filter invoices by status."""
        resp = httpx.get(
            f"{SERVER_URL}/api/invoices",
            params={"status": "draft"},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        for inv in data["invoices"]:
            assert inv["status"] == "draft"

    def test_invoice_has_line_items(self, auth_headers: dict):
        """Create invoice with line items and verify they appear."""
        inv_id, _ = _create_invoice(auth_headers, "lineitems", notes="Line item test")

        # Add line items
        for item in [
            {"item_type": "service", "description": "Diagnostic", "quantity": 1, "unit_price": 50},
            {"item_type": "part", "description": "Screen replacement", "quantity": 1, "unit_price": 120},
        ]:
            resp = httpx.post(
                f"{SERVER_URL}/api/invoices/{inv_id}/line-items",
                json=item,
                headers=auth_headers, timeout=10,
            )
            assert_ok(resp)

        # Fetch line items
        r3 = httpx.get(
            f"{SERVER_URL}/api/invoices/{inv_id}/line-items",
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(r3)
        assert len(data["line_items"]) >= 2
        descriptions = [li["description"] for li in data["line_items"]]
        assert "Diagnostic" in descriptions
        assert "Screen replacement" in descriptions

    def test_delete_line_item(self, auth_headers: dict):
        """Delete a single line item."""
        inv_id, _ = _create_invoice(auth_headers, "delline", notes="Delete line")

        httpx.post(f"{SERVER_URL}/api/invoices/{inv_id}/line-items", json={"description": "To Delete", "quantity": 1, "unit_price": 10}, headers=auth_headers, timeout=10)

        # Get the item ID
        r2 = httpx.get(f"{SERVER_URL}/api/invoices/{inv_id}/line-items", headers=auth_headers, timeout=10)
        item_id = r2.json()["line_items"][0]["id"]

        resp = httpx.delete(
            f"{SERVER_URL}/api/invoices/{inv_id}/line-items/{item_id}",
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify gone
        r3 = httpx.get(f"{SERVER_URL}/api/invoices/{inv_id}/line-items", headers=auth_headers, timeout=10)
        ids = [li["id"] for li in r3.json()["line_items"]]
        assert item_id not in ids

    def test_update_invoice_status(self, auth_headers: dict):
        """Update invoice status to sent."""
        inv_id, _ = _create_invoice(auth_headers, "status", notes="Status test")
        resp = httpx.put(
            f"{SERVER_URL}/api/invoices/{inv_id}/status",
            json={"status": "sent"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_set_tax_rate(self, auth_headers: dict):
        """Set tax rate on an invoice."""
        inv_id, _ = _create_invoice(auth_headers, "tax", notes="Tax test")
        resp = httpx.put(
            f"{SERVER_URL}/api/invoices/{inv_id}/tax-rate",
            json={"tax_rate": 8.5},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_delete_invoice(self, auth_headers: dict):
        """Delete an invoice (admin only)."""
        inv_id, _ = _create_invoice(auth_headers, "delete", notes="Delete test")
        resp = httpx.delete(
            f"{SERVER_URL}/api/invoices/{inv_id}",
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_pdf_generation(self, auth_headers: dict):
        """PDF endpoint returns application/pdf content."""
        inv_id, _ = _create_invoice(auth_headers, "pdf", notes="PDF test")
        resp = httpx.get(
            f"{SERVER_URL}/api/invoices/{inv_id}/pdf",
            headers=auth_headers, timeout=15,
        )
        assert resp.status_code == 200, f"PDF failed: {resp.text[:200]}"
        assert resp.headers.get("content-type", "").startswith("application/pdf"), (
            f"Expected PDF, got {resp.headers.get('content-type')}"
        )
        assert len(resp.content) > 500, f"PDF too small: {len(resp.content)} bytes"

    def test_full_workflow(self, auth_headers: dict):
        """Complete invoice lifecycle: create → add items → update status → PDF."""
        inv_id, _ = _create_invoice(auth_headers, "workflow", notes="Full workflow")

        # Add items
        httpx.post(f"{SERVER_URL}/api/invoices/{inv_id}/line-items", json={"description": "Labor", "quantity": 2, "unit_price": 75}, headers=auth_headers, timeout=10)
        httpx.post(f"{SERVER_URL}/api/invoices/{inv_id}/line-items", json={"description": "Part", "quantity": 1, "unit_price": 200}, headers=auth_headers, timeout=10)

        # Set tax
        httpx.put(f"{SERVER_URL}/api/invoices/{inv_id}/tax-rate", json={"tax_rate": 7.0}, headers=auth_headers, timeout=10)

        # Send
        httpx.put(f"{SERVER_URL}/api/invoices/{inv_id}/status", json={"status": "sent"}, headers=auth_headers, timeout=10)

        # PDF
        pdf_resp = httpx.get(f"{SERVER_URL}/api/invoices/{inv_id}/pdf", headers=auth_headers, timeout=15)
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers.get("content-type", "").startswith("application/pdf")


class TestInvoiceErrors:
    """Invoice endpoint error handling."""

    def test_create_missing_customer(self, auth_headers: dict):
        """Create invoice with non-existent customer should not crash."""
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices",
            json={"customer_id": "no-such-customer-id", "notes": "", "due_date": 0},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code < 500, f"Server error on bad customer: {resp.text[:200]}"

    def test_create_missing_body(self, auth_headers: dict):
        """POST with empty body returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices",
            json={},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422

    def test_invalid_status(self, auth_headers: dict):
        """Setting an invalid status should not crash."""
        inv_id, _ = _create_invoice(auth_headers, "badstatus", notes="")
        resp = httpx.put(
            f"{SERVER_URL}/api/invoices/{inv_id}/status",
            json={"status": "nonexistent_status_xyzzy"},
            headers=auth_headers, timeout=10,
        )
        # STDB accepts any string for status — just don't crash
        assert resp.status_code < 500

    def test_pdf_nonexistent(self, auth_headers: dict):
        """PDF for non-existent invoice returns 404."""
        resp = httpx.get(
            f"{SERVER_URL}/api/invoices/nonexistent-id-99999/pdf",
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 404

    def test_unauthorized_access(self, client: httpx.Client):
        """All invoice endpoints require auth."""
        for path in ["/api/invoices", "/api/invoices/fake/pdf"]:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403), f"{path} allowed unauthenticated: {resp.status_code}"

    def test_overdue_count(self, auth_headers: dict):
        """Overdue count endpoint returns expected shape."""
        resp = httpx.get(f"{SERVER_URL}/api/invoices/overdue-count", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "count" in data
        assert "total" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["total"], (int, float))

    def test_trigger_overdue_check(self, auth_headers: dict):
        """Trigger overdue check returns ok."""
        resp = httpx.post(f"{SERVER_URL}/api/invoices/trigger-overdue-check", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert data["ok"] is True
        assert "marked" in data
        assert isinstance(data["marked"], int)

    def test_overdue_count_unauthorized(self, client: httpx.Client):
        """Overdue count requires auth."""
        resp = client.get("/api/invoices/overdue-count", timeout=10)
        assert resp.status_code in (401, 403)

    def test_trigger_overdue_unauthorized(self, client: httpx.Client):
        """Trigger overdue check requires auth."""
        resp = client.post("/api/invoices/trigger-overdue-check", timeout=10)
        assert resp.status_code in (401, 403)

    def test_summary(self, auth_headers: dict):
        """Summary endpoint returns expected shape."""
        resp = httpx.get(f"{SERVER_URL}/api/invoices/summary", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "by_status" in data
        assert "total_count" in data
        assert "total_revenue" in data
        assert "total_outstanding" in data
        assert "overdue_count" in data
        assert "overdue_total" in data
        assert isinstance(data["total_count"], int)

    def test_bulk_status_update(self, auth_headers: dict):
        """Bulk status update changes invoice statuses."""
        # Create our own invoices to ensure isolation
        inv_id1, _ = _create_invoice(auth_headers, "bulk1")
        inv_id2, _ = _create_invoice(auth_headers, "bulk2")
        ids = [inv_id1, inv_id2]
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices/bulk-status-update",
            json={"invoice_ids": ids, "status": "sent"},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data["ok"] is True
        assert data["updated"] >= 1
        assert data["errors"] == 0

    def test_summary_unauthorized(self, client: httpx.Client):
        """Summary requires auth."""
        resp = client.get("/api/invoices/summary", timeout=10)
        assert resp.status_code in (401, 403)

    def test_bulk_status_unauthorized(self, client: httpx.Client):
        """Bulk status update requires auth."""
        resp = client.post("/api/invoices/bulk-status-update", json={"invoice_ids": ["fake"], "status": "sent"}, timeout=10)
        assert resp.status_code in (401, 403)

    def test_send_overdue_reminders(self, auth_headers: dict):
        """Send overdue reminders returns expected shape."""
        resp = httpx.post(f"{SERVER_URL}/api/invoices/send-overdue-reminders", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert data["ok"] is True
        assert "email" in data
        assert "sms" in data
        assert "total" in data
        assert isinstance(data["email"], int)
        assert isinstance(data["sms"], int)

    def test_send_overdue_reminders_unauthorized(self, client: httpx.Client):
        """Send overdue reminders requires auth."""
        resp = client.post("/api/invoices/send-overdue-reminders", timeout=10)
        assert resp.status_code in (401, 403)


class TestInvoiceEmailQueue:
    """Invoice email delivery endpoints."""

    def test_send_email_requires_invoice_id(self, auth_headers: dict):
        """Send email endpoint rejects missing invoice_id."""
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices/send-email",
            json={},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 400

    def test_send_email_nonexistent(self, auth_headers: dict):
        """Send email on nonexistent invoice returns 404."""
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices/send-email",
            json={"invoice_id": "nonexistent"},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 404

    def test_send_email_valid(self, auth_headers: dict):
        """Send email on valid invoice returns ok."""
        # Create our own invoice
        inv_id, _ = _create_invoice(auth_headers, "sendmail", notes="Email test")
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices/send-email",
            json={"invoice_id": inv_id},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data["ok"] is True
        assert "sent_to" in data

    def test_send_email_unauthorized(self, client: httpx.Client):
        """Send email requires auth."""
        resp = client.post("/api/invoices/send-email", json={"invoice_id": "x"}, timeout=10)
        assert resp.status_code in (401, 403)

    def test_batch_email_empty_ids(self, auth_headers: dict):
        """Batch email rejects empty invoice_ids array."""
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices/send-batch-email",
            json={"invoice_ids": []},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 400

    def test_batch_email_valid(self, auth_headers: dict):
        """Batch email on valid invoices returns ok."""
        # Create our own invoices
        inv_id1, _ = _create_invoice(auth_headers, "batch1")
        inv_id2, _ = _create_invoice(auth_headers, "batch2")
        ids = [inv_id1, inv_id2]
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices/send-batch-email",
            json={"invoice_ids": ids},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data["ok"] is True
        assert "sent" in data
        assert "failed" in data
        assert "skipped" in data

    def test_batch_email_unauthorized(self, client: httpx.Client):
        """Batch email requires auth."""
        resp = client.post("/api/invoices/send-batch-email", json={"invoice_ids": ["x"]}, timeout=10)
        assert resp.status_code in (401, 403)

    def test_email_queue_status(self, auth_headers: dict):
        """Email queue status returns sends list."""
        resp = httpx.get(f"{SERVER_URL}/api/invoices/email-queue-status", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "sends" in data
        assert "count" in data
        assert isinstance(data["sends"], list)
        assert isinstance(data["count"], int)

    def test_email_queue_status_unauthorized(self, client: httpx.Client):
        """Email queue status requires auth."""
        resp = client.get("/api/invoices/email-queue-status", timeout=10)
        assert resp.status_code in (401, 403)
