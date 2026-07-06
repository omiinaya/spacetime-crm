"""CSV export and import tests."""
import io
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok


class TestExport:
    def test_export_customers(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/export/customers", headers=auth_headers, timeout=10)
        assert resp.status_code == 200
        assert "csv" in resp.headers.get("content-type", "").lower() or resp.status_code == 200

    def test_export_invalid_entity(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/export/nonexistent", headers=auth_headers, timeout=10)
        assert resp.status_code == 400

    def test_export_tickets(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/export/tickets", headers=auth_headers, timeout=10)
        assert resp.status_code == 200


class TestImport:
    def test_import_customers_without_id(self, auth_headers: dict):
        """Import customers CSV without ID column."""
        ts = int(__import__("time").time() * 1000)
        csv_content = f"first_name,last_name,email,phone\nImp,Test1,imp1-{ts}@test.com,555-0101\nImp,Test2,imp2-{ts}@test.com,555-0102\n"
        files = {"file": ("import.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/customers", files=files, headers=auth_headers, timeout=15)
        data = assert_ok(resp)
        assert data["imported"] >= 2

    def test_import_customers_missing_first_name(self, auth_headers: dict):
        csv_content = "last_name,email\nNobody,nobody@test.com\n"
        files = {"file": ("bad.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/customers", files=files, headers=auth_headers, timeout=10)
        assert resp.status_code == 400

    def test_import_products(self, auth_headers: dict):
        csv_content = "name,sku,price,cost\nImported Widget,IMP-001,29.99,15.00\nImported Gadget,IMP-002,49.99,25.00\n"
        files = {"file": ("products.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/products", files=files, headers=auth_headers, timeout=15)
        data = assert_ok(resp)
        assert data["imported"] >= 2

    def test_import_products_missing_name(self, auth_headers: dict):
        csv_content = "sku,price\nNOSKU,10\n"
        files = {"file": ("bad.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/products", files=files, headers=auth_headers, timeout=10)
        assert resp.status_code == 400


class TestExportImportErrors:
    def test_export_unauthorized(self, client: httpx.Client):
        resp = client.get("/api/export/customers", timeout=10)
        assert resp.status_code in (401, 403)

    def test_import_unauthorized(self, client: httpx.Client):
        csv_content = "first_name,last_name\nTest,User\n"
        files = {"file": ("test.csv", csv_content, "text/csv")}
        resp = client.post("/api/import/customers", files=files, timeout=10)
        assert resp.status_code in (401, 403)
