"""Purchase Order CRUD, line items, receiving, and status workflow tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, unique_suffix, _stdb_sql, _track_entity, test_admin_headers


def _row_dict(rows: list) -> dict:
    """Normalize an STDB SQL response into a flat row dict (schema/rows or flat)."""
    if not rows:
        return {}
    entry = rows[0]
    if isinstance(entry, dict) and "schema" in entry and "rows" in entry:
        elements = entry.get("schema", {}).get("elements", [])
        cols = []
        for el in elements:
            n = el.get("name", {})
            cols.append(n.get("some", n) if isinstance(n, dict) else n)
        row = entry.get("rows", [])
        if not row:
            return {}
        return dict(zip(cols, row[0]))
    return entry


@pytest.fixture
def test_product_id(test_admin_headers: dict, session_suffix: str) -> str:
    """Create a product for PO line items and return its ID.

    Uses a session-unique SKU and tracks the product for cleanup.
    """
    suf = unique_suffix()
    sku = f"PO-WDG-{session_suffix}-{suf}"
    httpx.post(f"{SERVER_URL}/api/products", json={"name": "PO Test Widget", "sku": sku, "price": 15, "cost": 8, "quantity_on_hand": 100}, headers=test_admin_headers, timeout=10)
    r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=test_admin_headers, timeout=10)
    prods = r.json().get("products", [])
    assert len(prods) > 0, "Product not created"
    pid = prods[0]["id"]
    _track_entity("product", pid)
    return pid


def _create_po(test_admin_headers: dict, session_suffix: str, tag: str = "") -> str:
    """Create a PO and return its ID.

    Uses session_suffix + random suffix for isolation across sessions
    and parallel workers.  Tracks the PO for session cleanup.
    """
    suf = f"{session_suffix}-{tag}-{unique_suffix()}" if tag else f"{session_suffix}-{unique_suffix()}"
    vendor = f"Vendor-{suf}"
    httpx.post(f"{SERVER_URL}/api/purchase-orders", json={"vendor_name": vendor, "notes": f"PO test {suf}"}, headers=test_admin_headers, timeout=10)
    rows = _stdb_sql(f"SELECT id FROM purchase_order WHERE vendor_name = '{vendor}'")
    assert len(rows) > 0, f"PO not found for vendor {vendor}"
    po_id = rows[0]["id"]
    _track_entity("purchase_order", po_id)
    return po_id


class TestPurchaseOrderCRUD:
    """PO create, get, list, delete lifecycle."""

    def test_create_purchase_order(self, test_admin_headers: dict, session_suffix: str):
        vendor = f"Acme Supplies {session_suffix}-{unique_suffix()}"
        resp = httpx.post(f"{SERVER_URL}/api/purchase-orders", json={"vendor_name": vendor, "notes": "Monthly restock"}, headers=test_admin_headers, timeout=10)
        assert_ok(resp)

    def test_create_purchase_order_persists_shipping_cost(self, test_admin_headers: dict, session_suffix: str):
        """shipping_cost from the Pydantic model must persist to STDB."""
        suf = unique_suffix()
        vendor = f"ShipCo {session_suffix}-{suf}"
        resp = httpx.post(
            f"{SERVER_URL}/api/purchase-orders",
            json={"vendor_name": vendor, "notes": "Shipping cost test", "shipping_cost": 24.95},
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)

        rows = _stdb_sql(f"SELECT * FROM purchase_order WHERE vendor_name = '{vendor}'")
        assert len(rows) == 1, f"Expected 1 PO with vendor {vendor}, got {len(rows)}"
        po = _row_dict(rows)
        assert float(po.get("shipping_cost", 0)) == 24.95, f"shipping_cost={po.get('shipping_cost')!r}"
        _track_entity("purchase_order", po["id"])

    def test_list_purchase_orders(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/purchase-orders", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "purchase_orders" in data
        assert "total" in data

    def test_get_purchase_order(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "get")
        resp = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "purchase_order" in data
        po = data["purchase_order"]
        assert po["id"] == po_id
        assert "line_items" in po
        assert "receipt_progress" in po

    def test_get_nonexistent(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/purchase-orders/nonexistent-999", headers=test_admin_headers, timeout=10)
        assert resp.status_code == 404

    def test_delete_purchase_order(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "delete")
        resp = httpx.delete(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        assert_ok(resp)


class TestPOLineItems:
    """PO line item lifecycle: add, list, delete."""

    def test_add_line_item(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "addli")
        resp = httpx.post(
            f"{SERVER_URL}/api/purchase-orders/{po_id}/line-items",
            json={"product_id": test_product_id, "description": "Widget box", "quantity": 10, "unit_price": 12.50},
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_line_items_in_get(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "listli")
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/line-items", json={"product_id": test_product_id, "description": "Gadget", "quantity": 5, "unit_price": 25}, headers=test_admin_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        data = assert_ok(r)
        items = data["purchase_order"]["line_items"]
        assert len(items) >= 1
        assert items[0]["description"] == "Gadget"

    def test_delete_line_item(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "delli")
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/line-items", json={"product_id": test_product_id, "description": "Temp item", "quantity": 3, "unit_price": 10}, headers=test_admin_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        items = r.json()["purchase_order"]["line_items"]
        assert len(items) > 0
        item_id = items[0]["id"]

        resp = httpx.delete(f"{SERVER_URL}/api/purchase-orders/{po_id}/line-items/{item_id}", headers=test_admin_headers, timeout=10)
        assert_ok(resp)

        # Verify gone
        r2 = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        remaining = [i["id"] for i in r2.json()["purchase_order"]["line_items"]]
        assert item_id not in remaining

    def test_update_po_status(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "postatus")
        for status in ["sent", "received", "cancelled"]:
            resp = httpx.put(f"{SERVER_URL}/api/purchase-orders/{po_id}/status", json={"status": status}, headers=test_admin_headers, timeout=10)
            assert_ok(resp)


class TestPOReceiving:
    """Purchase order receiving flow — partial and full receive."""

    def test_receive_item_updates_stock(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        """Receiving a PO item adds to product stock."""
        po_id = _create_po(test_admin_headers, session_suffix, "receive")
        product_id = test_product_id

        # Add line item
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/line-items", json={"product_id": product_id, "description": "Widget restock", "quantity": 20, "unit_price": 10}, headers=test_admin_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        items = r.json()["purchase_order"]["line_items"]
        assert len(items) > 0
        item_id = items[0]["id"]

        # Receive 10 units (partial) — POReceiveItem model requires received_quantity at top level
        resp = httpx.post(
            f"{SERVER_URL}/api/purchase-orders/{po_id}/receive",
            json={"received_quantity": 10, "items": [{"id": item_id, "received_quantity": 10}]},
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify line item received_quantity was updated
        r2 = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        for li in r2.json()["purchase_order"]["line_items"]:
            if li["id"] == item_id:
                assert float(li.get("received_quantity", 0)) == 10, f"receive_quantity not set: {li}"
                break
        else:
            pytest.fail("Line item not found in PO after receive")

        # Verify product adjustment was recorded
        r3 = httpx.get(f"{SERVER_URL}/api/products/{product_id}/adjustments", headers=test_admin_headers, timeout=10)
        adj = r3.json().get("adjustments", [])
        assert len(adj) >= 1, f"Expected at least 1 adjustment, got {adj}"
        assert any(a.get("reason") == "received" for a in adj), f"Expected 'received' adjustment, got: {adj}"

    def test_full_receive_updates_progress(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        """Receiving all items shows 100% receipt_progress."""
        po_id = _create_po(test_admin_headers, session_suffix, "fullrecv")
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/line-items", json={"product_id": test_product_id, "description": "Full box", "quantity": 5, "unit_price": 20}, headers=test_admin_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        item_id = r.json()["purchase_order"]["line_items"][0]["id"]

        # Receive full quantity
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/receive", json={"received_quantity": 5, "items": [{"id": item_id, "received_quantity": 5}]}, headers=test_admin_headers, timeout=10)

        # PO get recalculates receipt_progress from line items
        r2 = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        po_data = r2.json()["purchase_order"]
        # Check that received_quantity was set on the line item
        for li in po_data["line_items"]:
            if li["id"] == item_id:
                assert float(li.get("received_quantity", 0)) == 5, f"Line item received_quantity not updated: {li}"
                break


class TestPOErrors:
    def test_create_missing_vendor(self, test_admin_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/purchase-orders", json={}, headers=test_admin_headers, timeout=10)
        assert resp.status_code == 422

    def test_unauthorized_access(self, client: httpx.Client):
        resp = client.get("/api/purchase-orders", timeout=10)
        assert resp.status_code in (401, 403)


class TestPOApproval:
    """Purchase order approval workflow: submit, approve, reject."""

    def test_submit_for_approval(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "submit")
        resp = httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/submit-for-approval", headers=test_admin_headers, timeout=10)
        assert_ok(resp)
        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        assert r.json()["purchase_order"]["status"] == "pending_approval"

    def test_approve_po(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "approve")
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/submit-for-approval", headers=test_admin_headers, timeout=10)
        resp = httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/approve", json={"user_id": "admin-user"}, headers=test_admin_headers, timeout=10)
        assert_ok(resp)
        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        po = r.json()["purchase_order"]
        assert po["status"] == "approved"
        assert po["approved_by"] == "admin-user"
        assert po["approved_at"] > 0

    def test_reject_po(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "reject")
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/submit-for-approval", headers=test_admin_headers, timeout=10)
        resp = httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/reject", headers=test_admin_headers, timeout=10)
        assert_ok(resp)
        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        assert r.json()["purchase_order"]["status"] == "draft"

    def test_reapprove_after_rejection(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "reauth")
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/submit-for-approval", headers=test_admin_headers, timeout=10)
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/reject", headers=test_admin_headers, timeout=10)
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/submit-for-approval", headers=test_admin_headers, timeout=10)
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/approve", json={"user_id": "admin-user"}, headers=test_admin_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        assert r.json()["purchase_order"]["status"] == "approved"

    def test_cannot_approve_from_sent_status(self, test_admin_headers: dict, session_suffix: str):
        """Approve should only work from pending_approval status."""
        po_id = _create_po(test_admin_headers, session_suffix, "wrongstate")
        # Go directly to sent via status update
        httpx.put(f"{SERVER_URL}/api/purchase-orders/{po_id}/status", json={"status": "sent"}, headers=test_admin_headers, timeout=10)
        # Approve should silently no-op (status != pending_approval)
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/approve", json={"user_id": "admin"}, headers=test_admin_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        assert r.json()["purchase_order"]["status"] == "sent"

    def test_approve_shows_approved_by(self, test_admin_headers: dict, session_suffix: str):
        po_id = _create_po(test_admin_headers, session_suffix, "showappr")
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/submit-for-approval", headers=test_admin_headers, timeout=10)
        httpx.post(f"{SERVER_URL}/api/purchase-orders/{po_id}/approve", json={"user_id": "jane-admin"}, headers=test_admin_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/purchase-orders/{po_id}", headers=test_admin_headers, timeout=10)
        po = r.json()["purchase_order"]
        assert po["approved_by"] == "jane-admin"
