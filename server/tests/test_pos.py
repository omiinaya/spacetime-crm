"""POS / Counter Sale endpoint tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, unique_suffix


@pytest.fixture
def test_product_id(auth_headers: dict) -> str:
    """Create a product for POS line items and return its ID."""
    sku = f"POS-WDG-{unique_suffix()}"
    httpx.post(f"{SERVER_URL}/api/products", json={"name": "POS Widget", "sku": sku, "price": 19.99, "cost": 10, "quantity_on_hand": 50}, headers=auth_headers, timeout=10)
    r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=auth_headers, timeout=10)
    prods = r.json().get("products", [])
    assert len(prods) > 0, "Product not created"
    return prods[0]["id"]


def _create_sale(auth_headers: dict, suffix: str = "") -> str:
    """Create a counter sale and return its ID."""
    httpx.post(f"{SERVER_URL}/api/pos/create", json={
        "customer_name": f"Walk-in {suffix}",
        "payment_method": "cash",
        "amount_tendered": 100,
        "tax_rate": 8.25,
        "discount_amount": 0,
    }, headers=auth_headers, timeout=10)
    r = httpx.get(f"{SERVER_URL}/api/pos/sales", params={"limit": 1}, headers=auth_headers, timeout=10)
    sales = r.json().get("sales", [])
    assert len(sales) > 0
    return sales[0]["id"]


class TestPOSCRUD:
    """Counter sale lifecycle: create, list, get, delete."""

    def test_create_sale(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/pos/create", json={
            "customer_name": "Jane Customer",
            "payment_method": "card",
            "amount_tendered": 75,
            "tax_rate": 0,
            "discount_amount": 5,
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_list_sales(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "sales" in data
        assert "total" in data

    def test_get_sale(self, auth_headers: dict):
        sale_id = _create_sale(auth_headers, "get")
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "sale" in data
        assert data["sale"]["id"] == sale_id
        assert "line_items" in data["sale"]

    def test_get_nonexistent(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code in (404, 500)

    def test_delete_sale_admin_only(self, auth_headers: dict):
        sale_id = _create_sale(auth_headers, "delete")
        resp = httpx.delete(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_list_receipts(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/pos/receipts", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "receipts" in data
        assert "total" in data


class TestPOSItems:
    """Counter sale line item operations."""

    def test_add_item(self, auth_headers: dict, test_product_id: str):
        sale_id = _create_sale(auth_headers, "add")
        resp = httpx.post(f"{SERVER_URL}/api/pos/items", json={
            "sale_id": sale_id,
            "product_id": test_product_id,
            "product_name": "POS Widget",
            "sku": "POS-WDG-001",
            "quantity": 2,
            "unit_price": 19.99,
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

        # Verify totals updated
        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=auth_headers, timeout=10)
        sale = r.json()["sale"]
        assert sale["items_count"] >= 1
        assert sale["subtotal"] >= 39.98  # 2 * 19.99

    def test_multiple_items_update_totals(self, auth_headers: dict, test_product_id: str):
        sale_id = _create_sale(auth_headers, "multi")
        # Add first item
        httpx.post(f"{SERVER_URL}/api/pos/items", json={
            "sale_id": sale_id, "product_id": test_product_id,
            "product_name": "Widget A", "sku": "A-001",
            "quantity": 3, "unit_price": 10,
        }, headers=auth_headers, timeout=10)
        # Add second item
        httpx.post(f"{SERVER_URL}/api/pos/items", json={
            "sale_id": sale_id, "product_id": test_product_id,
            "product_name": "Widget B", "sku": "B-001",
            "quantity": 2, "unit_price": 5,
        }, headers=auth_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=auth_headers, timeout=10)
        sale = r.json()["sale"]
        assert sale["items_count"] == 2
        assert sale["subtotal"] == 40.0  # 30 + 10
        assert sale["tax_amount"] == 3.30  # 40 * 8.25 / 100
        assert sale["total"] == 43.30  # 40 + 3.30
        assert sale["change_due"] == 56.70  # 100 - 43.30

    def test_item_line_item_ordering(self, auth_headers: dict, test_product_id: str):
        sale_id = _create_sale(auth_headers, "order")
        for i in range(3):
            httpx.post(f"{SERVER_URL}/api/pos/items", json={
                "sale_id": sale_id, "product_id": test_product_id,
                "product_name": f"Item {i}", "sku": f"SKU-{i}",
                "quantity": 1, "unit_price": 10 + i,
            }, headers=auth_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=auth_headers, timeout=10)
        items = r.json()["sale"]["line_items"]
        assert len(items) == 3
        # Verify sort_order matches insertion order
        for idx, item in enumerate(items):
            assert item["sort_order"] == idx, f"Item {idx} has sort_order {item['sort_order']}"


class TestPOSRefund:
    """Counter sale refund operations."""

    def test_refund_sale(self, auth_headers: dict):
        sale_id = _create_sale(auth_headers, "refund")
        resp = httpx.post(f"{SERVER_URL}/api/pos/refund/{sale_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)

        r = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}", headers=auth_headers, timeout=10)
        assert r.json()["sale"]["status"] == "refunded"
        assert r.json()["sale"]["refunded_at"] > 0


class TestPOSReceiptPdf:
    """POS receipt PDF generation."""

    def test_receipt_pdf_returns_pdf(self, auth_headers: dict):
        """Getting receipt PDF for a completed sale returns PDF content type."""
        sale_id = _create_sale(auth_headers, "pdf")
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}/receipt-pdf", headers=auth_headers, timeout=10)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/pdf")
        content = resp.content
        assert len(content) > 200  # PDF is at least a few hundred bytes

    def test_receipt_pdf_nonexistent(self, auth_headers: dict):
        """Getting receipt PDF for a nonexistent sale returns 404."""
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/nonexistent-999/receipt-pdf", headers=auth_headers, timeout=10)
        assert resp.status_code == 404

    def test_receipt_pdf_requires_auth(self, client: httpx.Client):
        """Getting receipt PDF without auth returns 401."""
        resp = client.get(f"{SERVER_URL}/api/pos/sales/fake-id/receipt-pdf", timeout=10)
        assert resp.status_code in (401, 403)

    def test_receipt_pdf_has_content_disposition(self, auth_headers: dict):
        """Receipt PDF response includes a Content-Disposition header."""
        sale_id = _create_sale(auth_headers, "disp")
        resp = httpx.get(f"{SERVER_URL}/api/pos/sales/{sale_id}/receipt-pdf", headers=auth_headers, timeout=10)
        assert resp.status_code == 200
        assert "Content-Disposition" in resp.headers
        assert "receipt_" in resp.headers["content-disposition"]
        assert ".pdf" in resp.headers["content-disposition"]
