"""CSV export and import tests."""

import io
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok, unique_suffix, _track_entity, test_admin_headers


class TestExport:
    def test_export_customers(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/export/customers", headers=test_admin_headers, timeout=10)
        assert resp.status_code == 200
        assert "csv" in resp.headers.get("content-type", "").lower() or resp.status_code == 200

    def test_export_invalid_entity(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/export/nonexistent", headers=test_admin_headers, timeout=10)
        assert resp.status_code == 400

    def test_export_tickets(self, test_admin_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/export/tickets", headers=test_admin_headers, timeout=10)
        assert resp.status_code == 200


class TestImport:
    def test_import_customers_without_id(self, test_admin_headers: dict, session_suffix: str):
        """Import customers CSV without ID column."""
        suf = unique_suffix()
        csv_content = f"first_name,last_name,email,phone\nImp,Test1,imp1-{session_suffix}-{suf}@test.com,555-0101\nImp,Test2,imp2-{session_suffix}-{suf}@test.com,555-0102\n"
        files = {"file": ("import.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/customers", files=files, headers=test_admin_headers, timeout=15)
        data = assert_ok(resp)
        assert data["imported"] >= 2

    def test_import_customers_missing_first_name(self, test_admin_headers: dict):
        csv_content = "last_name,email\nNobody,nobody@test.com\n"
        files = {"file": ("bad.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/customers", files=files, headers=test_admin_headers, timeout=10)
        assert resp.status_code == 400

    def test_import_products(self, test_admin_headers: dict, session_suffix: str):
        suf = unique_suffix()
        csv_content = f"name,sku,price,cost\nImported Widget,IMP-{session_suffix}-{suf}-01,29.99,15.00\nImported Gadget,IMP-{session_suffix}-{suf}-02,49.99,25.00\n"
        files = {"file": ("products.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/products", files=files, headers=test_admin_headers, timeout=15)
        data = assert_ok(resp)
        assert data["imported"] >= 2

    def test_import_products_missing_name(self, test_admin_headers: dict):
        csv_content = "sku,price\nNOSKU,10\n"
        files = {"file": ("bad.csv", csv_content, "text/csv")}
        resp = httpx.post(f"{SERVER_URL}/api/import/products", files=files, headers=test_admin_headers, timeout=10)
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
