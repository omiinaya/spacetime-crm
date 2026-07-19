"""POS / Counter Sale endpoint tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, unique_suffix, _stdb_sql, _track_entity, test_admin_headers


@pytest.fixture
def test_product_id(test_admin_headers: dict, session_suffix: str) -> str:
    """Create a product for POS line items and return its ID."""
    sku = f"POS-WDG-{session_suffix}-{unique_suffix()}"
    httpx.post(f"{SERVER_URL}/api/products", json={"name": "POS Widget", "sku": sku, "price": 19.99, "cost": 10, "quantity_on_hand": 50}, headers=test_admin_headers, timeout=10)
    r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=test_admin_headers, timeout=10)
    prods = r.json().get("products", [])
    assert len(prods) > 0, "Product not created"
    pid = prods[0]["id"]
    _track_entity("product", pid)
    return pid


def _create_sale(test_admin_headers: dict, session_suffix: str = "", suffix: str = "") -> str:
    """Create a counter sale and return its ID.

    Uses unique customer_name and STDB SQL lookup for isolation.
    """
    suf = suffix or unique_suffix()
    name = f"Walk-in-{session_suffix}-{suf}"
    httpx.post(f"{SERVER_URL}/api/pos/create", json={
        "customer_name": name,
        "payment_method": "cash",
        "amount_tendered": 100,
        "tax_rate": 8.25,
        "discount_amount": 0,
    }, headers=test_admin_headers, timeout=10)
    rows = _stdb_sql(f"SELECT id FROM counter_sale WHERE customer_name = '{name}'")
    assert len(rows) > 0, f"Sale not found for customer '{name}'"
    sale_id = rows[0]["id"]
    _track_entity("counter_sale", sale_id)
    return sale_id


class TestPOSCRUD:
    """Counter sale lifecycle: create, list, get, delete."""

    def test_create_sale(self, test_admin_headers: dict, session_suffix: str):
        from .conftest import unique_suffix, test_admin_headers
        name = f"Jane Customer {session_suffix}-{unique_suffix()}"
        resp = httpx.post(f"{SERVER_URL}/api/pos/create", json={
            "customer_name": name,
            "payment_method": "card",
            "amount_tendered": 75,
            "tax_rate": 0,
            "discount_amount": 5,
        }, headers=test_admin_headers, timeout=10)
        assert_ok(resp)

    def test_list_sales(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "sales" in data
        assert "total" in data

    def test_get_sale(self, test_admin_headers: dict, session_suffix: str):
        sale_id = _create_sale(test_admin_headers, session_suffix, "get")
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "sale" in data
        assert data["sale"]["id"] == sale_id
        assert "line_items" in data["sale"]

    def test_get_nonexistent(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/nonexistent-999", headers=test_admin_headers, timeout=10)
        assert resp.status_code in (404, 500)

    def test_delete_sale_admin_only(self, test_admin_headers: dict, session_suffix: str):
        sale_id = _create_sale(test_admin_headers, session_suffix, "delete")
        resp = httpx.delete(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=test_admin_headers, timeout=10)
        assert_ok(resp)

    def test_list_receipts(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/pos/receipts", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "receipts" in data
        assert "total" in data


class TestPOSItems:
    """Counter sale line item operations."""

    def test_add_item(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        sale_id = _create_sale(test_admin_headers, session_suffix, "add")
        resp = httpx.post(f"{SERVER_URL}/api/pos/items", json={
            "sale_id": sale_id,
            "product_id": test_product_id,
            "product_name": "POS Widget",
            "sku": "POS-WDG-001",
            "quantity": 2,
            "unit_price": 19.99,
        }, headers=test_admin_headers, timeout=10)
        assert_ok(resp)

        # Verify totals updated
        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=test_admin_headers, timeout=10)
        sale = r.json()["sale"]
        assert sale["items_count"] >= 1
        assert sale["subtotal"] >= 39.98  # 2 * 19.99

    def test_multiple_items_update_totals(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        sale_id = _create_sale(test_admin_headers, session_suffix, "multi")
        # Add first item
        httpx.post(f"{SERVER_URL}/api/pos/items", json={
            "sale_id": sale_id, "product_id": test_product_id,
            "product_name": "Widget A", "sku": "A-001",
            "quantity": 3, "unit_price": 10,
        }, headers=test_admin_headers, timeout=10)
        # Add second item
        httpx.post(f"{SERVER_URL}/api/pos/items", json={
            "sale_id": sale_id, "product_id": test_product_id,
            "product_name": "Widget B", "sku": "B-001",
            "quantity": 2, "unit_price": 5,
        }, headers=test_admin_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=test_admin_headers, timeout=10)
        sale = r.json()["sale"]
        assert sale["items_count"] == 2
        assert sale["subtotal"] == 40.0  # 30 + 10
        assert sale["tax_amount"] == 3.30  # 40 * 8.25 / 100
        assert sale["total"] == 43.30  # 40 + 3.30
        assert sale["change_due"] == 56.70  # 100 - 43.30

    def test_item_line_item_ordering(self, test_admin_headers: dict, test_product_id: str, session_suffix: str):
        sale_id = _create_sale(test_admin_headers, session_suffix, "order")
        for i in range(3):
            httpx.post(f"{SERVER_URL}/api/pos/items", json={
                "sale_id": sale_id, "product_id": test_product_id,
                "product_name": f"Item {i}", "sku": f"SKU-{i}",
                "quantity": 1, "unit_price": 10 + i,
            }, headers=test_admin_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=test_admin_headers, timeout=10)
        items = r.json()["sale"]["line_items"]
        assert len(items) == 3
        # Verify sort_order matches insertion order
        for idx, item in enumerate(items):
            assert item["sort_order"] == idx, f"Item {idx} has sort_order {item['sort_order']}"


class TestPOSRefund:
    """Counter sale refund operations."""

    def test_refund_sale(self, test_admin_headers: dict, session_suffix: str):
        sale_id = _create_sale(test_admin_headers, session_suffix, "refund")
        resp = httpx.post(f"{SERVER_URL}/api/pos/refund/{sale_id}", headers=test_admin_headers, timeout=10)
        assert_ok(resp)

        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=test_admin_headers, timeout=10)
        assert r.json()["sale"]["status"] == "refunded"
        assert r.json()["sale"]["refunded_at"] > 0


class TestPOSReceiptPdf:
    """POS receipt PDF generation."""

    def test_receipt_pdf_returns_pdf(self, test_admin_headers: dict, session_suffix: str):
        """Getting receipt PDF for a completed sale returns PDF content type."""
        sale_id = _create_sale(test_admin_headers, session_suffix, "pdf")
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}/receipt-pdf", headers=test_admin_headers, timeout=10)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/pdf")
        content = resp.content
        assert len(content) > 200  # PDF is at least a few hundred bytes

    def test_receipt_pdf_nonexistent(self, test_admin_headers: dict):
        """Getting receipt PDF for a nonexistent sale returns 404."""
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/nonexistent-999/receipt-pdf", headers=test_admin_headers, timeout=10)
        assert resp.status_code == 404

    def test_receipt_pdf_requires_auth(self, client: httpx.Client):
        """Getting receipt PDF without auth returns 401."""
        resp = client.get(f"{SERVER_URL}/api/pos/sales/fake-id/receipt-pdf", timeout=10)
        assert resp.status_code in (401, 403)

    def test_receipt_pdf_has_content_disposition(self, test_admin_headers: dict, session_suffix: str):
        """Receipt PDF response includes a Content-Disposition header."""
        sale_id = _create_sale(test_admin_headers, session_suffix, "disp")
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}/receipt-pdf", headers=test_admin_headers, timeout=10)
        assert resp.status_code == 200
        assert "Content-Disposition" in resp.headers
        assert "receipt_" in resp.headers["content-disposition"]
        assert ".pdf" in resp.headers["content-disposition"]
