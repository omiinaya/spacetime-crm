"""Tax rate CRUD tests."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok, unique_suffix, _stdb_sql


def _create_rate(auth_headers: dict, suffix: str = "") -> str:
    """Create a tax rate and return its ID.

    Uses unique name and STDB SQL lookup for isolation.
    """
    suf = suffix or unique_suffix()
    name = f"Tax-{suf}"
    resp = httpx.post(f"{SERVER_URL}/api/tax-rates", json={
        "name": name, "rate": 8.25, "is_default": False,
    }, headers=auth_headers, timeout=10)
    assert_ok(resp)

    rows = _stdb_sql(f"SELECT id FROM tax_rate WHERE name = '{name}'")
    assert len(rows) >= 1, f"Tax rate not found with name '{name}'"
    return rows[0]["id"]


class TestTaxRateCRUD:
    def test_create(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/tax-rates", json={
            "name": "Sales Tax", "rate": 7.5, "is_default": False,
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_create_invalid_rate(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/tax-rates", json={
            "name": "Bad", "rate": 150, "is_default": False,
        }, headers=auth_headers, timeout=10)
        assert resp.status_code == 422

    def test_list(self, auth_headers: dict):
        _create_rate(auth_headers, "lst")
        resp = httpx.get(f"{SERVER_URL}/api/tax-rates", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "tax_rates" in data
        assert "total" in data

    def test_update(self, auth_headers: dict):
        rate_id = _create_rate(auth_headers, "upd")
        resp = httpx.put(f"{SERVER_URL}/api/tax-rates/{rate_id}", json={
            "name": "Updated Tax", "rate": 9.0, "is_default": True,
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_update_nonexistent(self, auth_headers: dict):
        resp = httpx.put(f"{SERVER_URL}/api/tax-rates/nonexistent-999", json={
            "name": "Nope", "rate": 5.0, "is_default": False,
        }, headers=auth_headers, timeout=10)
        assert resp.status_code < 500

    def test_delete(self, auth_headers: dict):
        rate_id = _create_rate(auth_headers, "del")
        resp = httpx.delete(f"{SERVER_URL}/api/tax-rates/{rate_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_delete_nonexistent(self, auth_headers: dict):
        resp = httpx.delete(f"{SERVER_URL}/api/tax-rates/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code < 500

    def test_set_default(self, auth_headers: dict):
        rate_id = _create_rate(auth_headers, "def")
        resp = httpx.put(f"{SERVER_URL}/api/tax-rates/{rate_id}", json={
            "name": "Default Tax", "rate": 6.0, "is_default": True,
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)


class TestTaxRateErrors:
    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/tax-rates", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post("/api/tax-rates", json={"name": "X", "rate": 5.0, "is_default": False}, timeout=10)
        assert resp.status_code in (401, 403)
