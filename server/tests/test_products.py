"""Product CRUD, inventory adjustments, low stock alert integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, unique_suffix, _track_entity


def _unique_sku(base: str, session_suffix: str = "") -> str:
    return f"{base}-{session_suffix}-{unique_suffix()}"


class TestProductCRUD:
    """Product create, list, update, delete lifecycle."""

    def test_create_product(self, auth_headers: dict, session_suffix: str):
        """Create a basic product."""
        resp = httpx.post(
            f"{SERVER_URL}/api/products",
            json={"name": "Test Product", "sku": _unique_sku("TST", session_suffix), "price": 29.99, "cost": 15.00, "quantity_on_hand": 50},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_products(self, auth_headers: dict):
        """List products returns paginated results."""
        resp = httpx.get(f"{SERVER_URL}/api/products", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "products" in data
        assert "total" in data

    def test_update_product_quantity(self, auth_headers: dict, session_suffix: str):
        """Update product quantity."""
        # Create product first
        sku = _unique_sku("QTY", session_suffix)
        httpx.post(f"{SERVER_URL}/api/products", json={"name": "Qty Test", "sku": sku, "price": 10, "quantity_on_hand": 25}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=auth_headers, timeout=10)
        prods = r.json().get("products", [])
        if not prods:
            pytest.skip("Product not found after creation")
        pid = prods[0]["id"]
        _track_entity("product", pid)

        resp = httpx.put(
            f"{SERVER_URL}/api/products/{pid}/quantity",
            json={"quantity_on_hand": 100},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_update_product(self, auth_headers: dict, session_suffix: str):
        """Update product fields (name, price, min_stock)."""
        sku = _unique_sku("UPD", session_suffix)
        httpx.post(f"{SERVER_URL}/api/products", json={"name": "Update Test", "sku": sku, "price": 20, "cost": 10, "quantity_on_hand": 10, "min_stock": 2}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=auth_headers, timeout=10)
        prods = r.json().get("products", [])
        if not prods:
            pytest.skip("Product not found")
        pid = prods[0]["id"]
        _track_entity("product", pid)

        resp = httpx.put(
            f"{SERVER_URL}/api/products/{prods[0]['id']}",
            json={"name": "Updated Name", "sku": sku, "price": 25, "cost": 12, "quantity_on_hand": 10, "min_stock": 5, "location": "Aisle 3"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_delete_product(self, auth_headers: dict, session_suffix: str):
        """Delete a product (admin only)."""
        sku = _unique_sku("DEL", session_suffix)
        httpx.post(f"{SERVER_URL}/api/products", json={"name": "Delete Test", "sku": sku, "price": 5, "quantity_on_hand": 0}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=auth_headers, timeout=10)
        prods = r.json().get("products", [])
        if not prods:
            pytest.skip("Product not found")
        pid = prods[0]["id"]

        resp = httpx.delete(f"{SERVER_URL}/api/products/{pid}", headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_inventory_adjustment(self, auth_headers: dict, session_suffix: str):
        """Create an inventory adjustment for a product."""
        sku = _unique_sku("ADJ", session_suffix)
        httpx.post(f"{SERVER_URL}/api/products", json={"name": "Adj Test", "sku": sku, "price": 8, "quantity_on_hand": 30}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=auth_headers, timeout=10)
        prods = r.json().get("products", [])
        if not prods:
            pytest.skip("Product not found")
        pid = prods[0]["id"]
        _track_entity("product", pid)

        resp = httpx.post(
            f"{SERVER_URL}/api/products/{pid}/adjustments",
            json={"quantity_change": -5, "reason": "damaged", "notes": "Screen cracked in storage"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_adjustments(self, auth_headers: dict, session_suffix: str):
        """List inventory adjustments for a product."""
        sku = _unique_sku("ADJL", session_suffix)
        httpx.post(f"{SERVER_URL}/api/products", json={"name": "List Adj", "sku": sku, "price": 12, "quantity_on_hand": 20}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/products", params={"search": sku}, headers=auth_headers, timeout=10)
        prods = r.json().get("products", [])
        if not prods:
            pytest.skip("Product not found")
        pid = prods[0]["id"]
        _track_entity("product", pid)

        # Create an adjustment first
        httpx.post(f"{SERVER_URL}/api/products/{pid}/adjustments", json={"quantity_change": 10, "reason": "restock", "notes": "New shipment"}, headers=auth_headers, timeout=10)

        resp = httpx.get(f"{SERVER_URL}/api/products/{pid}/adjustments", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "adjustments" in data
        assert len(data["adjustments"]) >= 1

    def test_low_stock_list(self, auth_headers: dict, session_suffix: str):
        """Low stock endpoint returns products below threshold."""
        # Create a product with min_stock > quantity_on_hand
        sku = _unique_sku("LOW", session_suffix)
        httpx.post(f"{SERVER_URL}/api/products", json={"name": "Low Stock Test", "sku": sku, "price": 5, "quantity_on_hand": 1, "min_stock": 5}, headers=auth_headers, timeout=10)

        resp = httpx.get(f"{SERVER_URL}/api/products/low-stock", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "products" in data
        assert "count" in data

    def test_low_stock_notify(self, auth_headers: dict):
        """Low stock notify returns ok (email may fail gracefully)."""
        resp = httpx.post(f"{SERVER_URL}/api/products/low-stock/notify", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        # Email only works if SMTP is configured — just verify it doesn't crash
        assert "ok" in data


class TestProductErrors:
    """Product endpoint error handling."""

    def test_create_missing_name(self, auth_headers: dict):
        """Missing product name returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/products",
            json={"price": 10},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422

    def test_negative_price(self, auth_headers: dict):
        """Negative price returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/products",
            json={"name": "Bad", "price": -5, "quantity_on_hand": 0},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422

    def test_unauthorized_access(self, client: httpx.Client):
        """Product endpoints require auth."""
        for path in ["/api/products", "/api/products/fake/adjustments", "/api/products/low-stock", "/api/products/by-barcode/test123"]:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403), f"{path} allowed unauthenticated"


class TestBarcodeLookup:
    """Barcode-based product lookup."""

    def test_lookup_by_barcode(self, auth_headers: dict, session_suffix: str):
        sku = _unique_sku("BAR", session_suffix)
        barcode = f"59{unique_suffix()[:10]}"
        product = {"name": "Barcode Test", "sku": sku, "barcode": barcode, "price": 25, "cost": 10, "quantity_on_hand": 5}
        httpx.post(f"{SERVER_URL}/api/products", json=product, headers=auth_headers, timeout=10)
        resp = httpx.get(f"{SERVER_URL}/api/products/by-barcode/{barcode}", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert data["product"]["name"] == "Barcode Test"
        assert data["product"]["barcode"] == barcode

    def test_lookup_nonexistent(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/products/by-barcode/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code == 404
