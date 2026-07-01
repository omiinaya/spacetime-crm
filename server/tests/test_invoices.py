"""Invoice CRUD, line items, tax, PDF, and status workflow integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer


def _create_test_customer(auth_headers: dict, suffix: str = "") -> str:
    """Create a customer and return their ID."""
    email = f"inv-cust-{suffix or 'main'}@example.com"
    c = create_customer(auth_headers, first_name="Invoice", last_name=f"Test{suffix}", email=email)
    cid = c.get("id")
    assert cid, f"Failed to create customer: {c}"
    return cid


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
        cid = _create_test_customer(auth_headers, "lineitems")
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices",
            json={"customer_id": cid, "notes": "Line item test", "due_date": 0},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Get the last invoice
        r2 = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1}, headers=auth_headers, timeout=10)
        invs = r2.json().get("invoices", [])
        assert len(invs) > 0
        inv_id = invs[0]["id"]

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
        cid = _create_test_customer(auth_headers, "delline")
        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "Delete line", "due_date": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1}, headers=auth_headers, timeout=10)
        inv_id = r.json()["invoices"][0]["id"]

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
        cid = _create_test_customer(auth_headers, "status")
        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "Status test", "due_date": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1, "status": "draft"}, headers=auth_headers, timeout=10)
        invs = r.json().get("invoices", [])
        if not invs:
            pytest.skip("No draft invoice available")
        inv_id = invs[0]["id"]

        resp = httpx.put(
            f"{SERVER_URL}/api/invoices/{inv_id}/status",
            json={"status": "sent"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_set_tax_rate(self, auth_headers: dict):
        """Set tax rate on an invoice."""
        cid = _create_test_customer(auth_headers, "tax")
        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "Tax test", "due_date": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1}, headers=auth_headers, timeout=10)
        inv_id = r.json()["invoices"][0]["id"]

        resp = httpx.put(
            f"{SERVER_URL}/api/invoices/{inv_id}/tax-rate",
            json={"tax_rate": 8.5},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_delete_invoice(self, auth_headers: dict):
        """Delete an invoice (admin only)."""
        cid = _create_test_customer(auth_headers, "delete")
        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "Delete test", "due_date": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1}, headers=auth_headers, timeout=10)
        inv_id = r.json()["invoices"][0]["id"]

        resp = httpx.delete(
            f"{SERVER_URL}/api/invoices/{inv_id}",
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_pdf_generation(self, auth_headers: dict):
        """PDF endpoint returns application/pdf content."""
        cid = _create_test_customer(auth_headers, "pdf")
        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "PDF test", "due_date": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1}, headers=auth_headers, timeout=10)
        inv_id = r.json()["invoices"][0]["id"]

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
        cid = _create_test_customer(auth_headers, "workflow")

        # Create
        resp = httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "Full workflow", "due_date": 0}, headers=auth_headers, timeout=10)
        assert_ok(resp)

        r = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1}, headers=auth_headers, timeout=10)
        inv_id = r.json()["invoices"][0]["id"]

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
        cid = _create_test_customer(auth_headers, "badstatus")
        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "", "due_date": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 1}, headers=auth_headers, timeout=10)
        inv_id = r.json()["invoices"][0]["id"]

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
        assert data["total_count"] > 0

    def test_bulk_status_update(self, auth_headers: dict):
        """Bulk status update changes invoice statuses."""
        # First get some invoice IDs
        list_resp = httpx.get(f"{SERVER_URL}/api/invoices", params={"limit": 3}, headers=auth_headers, timeout=10)
        invs = list_resp.json().get("invoices", [])
        if len(invs) < 2:
            pytest.skip("Need at least 2 invoices for bulk test")
        ids = [inv["id"] for inv in invs[:2]]
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
