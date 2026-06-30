"""Estimate CRUD, line items, status workflow, and conversion integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer


def _create_customer(auth_headers: dict, suffix: str = "") -> str:
    c = create_customer(auth_headers, first_name="Est", last_name=f"Test{suffix}", email=f"est-{suffix or 'main'}@example.com")
    return c["id"]


def _create_estimate(auth_headers: dict, suffix: str = "") -> str:
    cid = _create_customer(auth_headers, suffix)
    httpx.post(f"{SERVER_URL}/api/estimates", json={"customer_id": cid, "notes": f"Est test {suffix}", "expires_at": 0}, headers=auth_headers, timeout=10)
    r = httpx.get(f"{SERVER_URL}/api/estimates", params={"limit": 1}, headers=auth_headers, timeout=10)
    ests = r.json().get("estimates", [])
    assert len(ests) > 0
    return ests[0]["id"]


class TestEstimateCRUD:
    """Estimate create, list, line items, status workflow."""

    def test_create_estimate(self, auth_headers: dict):
        cid = _create_customer(auth_headers, "create")
        resp = httpx.post(
            f"{SERVER_URL}/api/estimates",
            json={"customer_id": cid, "notes": "Test estimate", "expires_at": 0},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_estimates(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/estimates", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "estimates" in data
        assert "total" in data

    def test_list_estimates_filter_by_status(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/estimates", params={"status": "draft"}, headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        for est in data["estimates"]:
            assert est["status"] == "draft"

    def test_add_line_items(self, auth_headers: dict):
        est_id = _create_estimate(auth_headers, "lineitems")

        for item in [
            {"description": "Labor - 2hrs", "quantity": 2, "unit_price": 65},
            {"description": "Diagnostic fee", "quantity": 1, "unit_price": 49.99},
        ]:
            resp = httpx.post(
                f"{SERVER_URL}/api/estimates/{est_id}/line-items",
                json=item,
                headers=auth_headers, timeout=10,
            )
            assert_ok(resp)

        r = httpx.get(f"{SERVER_URL}/api/estimates/{est_id}/line-items", headers=auth_headers, timeout=10)
        data = assert_ok(r)
        assert len(data["line_items"]) >= 2

    def test_update_status(self, auth_headers: dict):
        est_id = _create_estimate(auth_headers, "status")

        for status in ["sent", "approved", "rejected"]:
            resp = httpx.put(
                f"{SERVER_URL}/api/estimates/{est_id}/status",
                json={"status": status},
                headers=auth_headers, timeout=10,
            )
            assert_ok(resp)

    def test_delete_estimate(self, auth_headers: dict):
        est_id = _create_estimate(auth_headers, "delete")
        resp = httpx.delete(f"{SERVER_URL}/api/estimates/{est_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)


class TestEstimateConversion:
    """Estimate-to-invoice conversion workflow."""

    def test_convert_approved_estimate(self, auth_headers: dict):
        """Full conversion: create estimate → approve → convert → get invoice."""
        cid = _create_customer(auth_headers, "convert")
        httpx.post(f"{SERVER_URL}/api/estimates", json={"customer_id": cid, "notes": "Will convert", "expires_at": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/estimates", params={"limit": 1}, headers=auth_headers, timeout=10)
        est_id = r.json()["estimates"][0]["id"]

        # Add line item (so estimate has content)
        httpx.post(f"{SERVER_URL}/api/estimates/{est_id}/line-items", json={"description": "Repair service", "quantity": 1, "unit_price": 150}, headers=auth_headers, timeout=10)

        # Approve
        httpx.put(f"{SERVER_URL}/api/estimates/{est_id}/status", json={"status": "approved"}, headers=auth_headers, timeout=10)

        # Convert
        resp = httpx.post(f"{SERVER_URL}/api/estimates/{est_id}/convert", headers=auth_headers, timeout=15)
        data = assert_ok(resp)
        assert data.get("ok") is True
        invoice_id = data.get("invoice_id", "")
        assert invoice_id, f"Expected invoice_id in response: {data}"

        # Verify invoice exists
        r2 = httpx.get(f"{SERVER_URL}/api/invoices", headers=auth_headers, timeout=10)
        inv_ids = [inv["id"] for inv in r2.json().get("invoices", [])]
        assert invoice_id in inv_ids, f"Invoice {invoice_id} not found in list"

    def test_convert_non_approved_rejected(self, auth_headers: dict):
        """Only approved estimates can be converted."""
        est_id = _create_estimate(auth_headers, "noconvert")

        resp = httpx.post(f"{SERVER_URL}/api/estimates/{est_id}/convert", headers=auth_headers, timeout=10)
        assert resp.status_code == 400, f"Expected 400 for non-approved, got {resp.status_code}: {resp.text[:200]}"

    def test_convert_nonexistent(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/estimates/nonexistent-id-99999/convert", headers=auth_headers, timeout=10)
        assert resp.status_code == 404


class TestEstimateErrors:
    def test_create_missing_customer(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/estimates", json={"notes": "No customer"}, headers=auth_headers, timeout=10)
        assert resp.status_code == 422

    def test_delete_nonexistent(self, auth_headers: dict):
        resp = httpx.delete(f"{SERVER_URL}/api/estimates/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code < 500

    def test_unauthorized_access(self, client: httpx.Client):
        for path in ["/api/estimates"]:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403)
