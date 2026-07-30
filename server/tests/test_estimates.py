"""Estimate CRUD, line items, status workflow, and conversion integration tests."""

import httpx

from .conftest import (
    SERVER_URL,
    _stdb_sql,
    _track_entity,
    assert_ok,
    create_customer,
    unique_suffix,
)


def _create_customer(
    test_admin_headers: dict, session_suffix: str = "", suffix: str = ""
) -> str:
    suf = suffix or unique_suffix()
    c = create_customer(
        test_admin_headers,
        session_suffix=session_suffix,
        first_name="Est",
        last_name=f"Test{suf}",
        email=f"est-{session_suffix}-{suf}@example.com",
    )
    return c["id"]


def _create_estimate(
    test_admin_headers: dict, session_suffix: str = "", suffix: str = ""
) -> str:
    cid = _create_customer(test_admin_headers, session_suffix, suffix)
    notes = f"Est test {session_suffix}-{suffix or unique_suffix()}"
    httpx.post(
        f"{SERVER_URL}/api/estimates",
        json={"customer_id": cid, "notes": notes, "expires_at": 0},
        headers=test_admin_headers,
        timeout=10,
    )
    result = _stdb_sql(f"SELECT id FROM estimates WHERE notes = '{notes}'")
    assert len(result) == 1, (
        f"Expected 1 table result for estimate with notes '{notes}'"
    )
    table = result[0]
    assert table.get("rows") and len(table["rows"]) >= 1, (
        f"Estimate not found for notes '{notes}'"
    )
    eid = table["rows"][0][0]  # id is first (and only) column
    _track_entity("estimate", eid)
    return eid


class TestEstimateCRUD:
    """Estimate create, list, line items, status workflow."""

    def test_create_estimate(self, test_admin_headers: dict, session_suffix: str):
        cid = _create_customer(test_admin_headers, session_suffix, "create")
        from .conftest import unique_suffix

        notes = f"Test estimate {session_suffix}-{unique_suffix()}"
        resp = httpx.post(
            f"{SERVER_URL}/api/estimates",
            json={"customer_id": cid, "notes": notes, "expires_at": 0},
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_list_estimates(self, test_admin_headers: dict):
        resp = httpx.get(
            f"{SERVER_URL}/api/estimates", headers=test_admin_headers, timeout=10
        )
        data = assert_ok(resp)
        assert "estimates" in data
        assert "total" in data

    def test_list_estimates_filter_by_status(self, test_admin_headers: dict):
        resp = httpx.get(
            f"{SERVER_URL}/api/estimates",
            params={"status": "draft"},
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        for est in data["estimates"]:
            assert est["status"] == "draft"

    def test_add_line_items(self, test_admin_headers: dict, session_suffix: str):
        est_id = _create_estimate(test_admin_headers, session_suffix, "lineitems")

        for item in [
            {"description": "Labor - 2hrs", "quantity": 2, "unit_price": 65},
            {"description": "Diagnostic fee", "quantity": 1, "unit_price": 49.99},
        ]:
            resp = httpx.post(
                f"{SERVER_URL}/api/estimates/{est_id}/line-items",
                json=item,
                headers=test_admin_headers,
                timeout=10,
            )
            assert_ok(resp)

        r = httpx.get(
            f"{SERVER_URL}/api/estimates/{est_id}/line-items",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(r)
        assert len(data["line_items"]) >= 2

    def test_update_status(self, test_admin_headers: dict, session_suffix: str):
        est_id = _create_estimate(test_admin_headers, session_suffix, "status")

        for status in ["sent", "approved", "rejected"]:
            resp = httpx.put(
                f"{SERVER_URL}/api/estimates/{est_id}/status",
                json={"status": status},
                headers=test_admin_headers,
                timeout=10,
            )
            assert_ok(resp)

    def test_delete_estimate(self, test_admin_headers: dict, session_suffix: str):
        est_id = _create_estimate(test_admin_headers, session_suffix, "delete")
        resp = httpx.delete(
            f"{SERVER_URL}/api/estimates/{est_id}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)


class TestEstimateConversion:
    """Estimate-to-invoice conversion workflow."""

    def test_convert_approved_estimate(
        self, test_admin_headers: dict, session_suffix: str
    ):
        """Full conversion: create estimate → approve → convert → get invoice."""
        est_id = _create_estimate(test_admin_headers, session_suffix, "convert")

        # Add line item (so estimate has content)
        httpx.post(
            f"{SERVER_URL}/api/estimates/{est_id}/line-items",
            json={"description": "Repair service", "quantity": 1, "unit_price": 150},
            headers=test_admin_headers,
            timeout=10,
        )

        # Approve
        httpx.put(
            f"{SERVER_URL}/api/estimates/{est_id}/status",
            json={"status": "approved"},
            headers=test_admin_headers,
            timeout=10,
        )

        # Convert
        resp = httpx.post(
            f"{SERVER_URL}/api/estimates/{est_id}/convert",
            headers=test_admin_headers,
            timeout=15,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True
        invoice_id = data.get("invoice_id", "")
        assert invoice_id, f"Expected invoice_id in response: {data}"

        # Verify invoice exists (high limit to account for accumulated test data)
        r2 = httpx.get(
            f"{SERVER_URL}/api/invoices",
            params={"limit": 500},
            headers=test_admin_headers,
            timeout=10,
        )
        inv_ids = [inv["id"] for inv in r2.json().get("invoices", [])]
        assert invoice_id in inv_ids, f"Invoice {invoice_id} not found in list"

    def test_convert_non_approved_rejected(
        self, test_admin_headers: dict, session_suffix: str
    ):
        """Only approved estimates can be converted."""
        est_id = _create_estimate(test_admin_headers, session_suffix, "noconvert")

        resp = httpx.post(
            f"{SERVER_URL}/api/estimates/{est_id}/convert",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400, (
            f"Expected 400 for non-approved, got {resp.status_code}: {resp.text[:200]}"
        )

    def test_convert_nonexistent(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/estimates/nonexistent-id-99999/convert",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 404


class TestEstimateErrors:
    def test_create_missing_customer(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/estimates",
            json={"notes": "No customer"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_delete_nonexistent(self, test_admin_headers: dict):
        resp = httpx.delete(
            f"{SERVER_URL}/api/estimates/nonexistent-999",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500

    def test_unauthorized_access(self, client: httpx.Client):
        for path in ["/api/estimates"]:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403)
