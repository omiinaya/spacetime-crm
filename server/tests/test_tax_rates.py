"""Tax rate CRUD tests."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok, unique_suffix, _stdb_sql, save_default_tax_rate, restore_default_tax_rate, _track_entity, test_admin_headers


def _create_rate(test_admin_headers: dict, session_suffix: str = "", suffix: str = "") -> str:
    """Create a tax rate and return its ID.

    Uses unique name + session_suffix for isolation and cleanup.
    """
    suf = suffix or unique_suffix()
    name = f"Tax-{session_suffix}-{suf}"
    resp = httpx.post(f"{SERVER_URL}/api/tax-rates", json={
        "name": name, "rate": 8.25, "is_default": False,
    }, headers=test_admin_headers, timeout=10)
    assert_ok(resp)

    rows = _stdb_sql(f"SELECT id FROM tax_rate WHERE name = '{name}'")
    assert len(rows) >= 1, f"Tax rate not found with name '{name}'"
    rate_id = rows[0]["id"]
    _track_entity("tax_rate", rate_id)
    return rate_id


class TestTaxRateCRUD:
    def test_create(self, test_admin_headers: dict, session_suffix: str):
        from .conftest import unique_suffix, test_admin_headers
        name = f"Sales Tax {session_suffix}-{unique_suffix()}"
        resp = httpx.post(f"{SERVER_URL}/api/tax-rates", json={
            "name": name, "rate": 7.5, "is_default": False,
        }, headers=test_admin_headers, timeout=10)
        assert_ok(resp)
        # Track for session cleanup
        rows = _stdb_sql(f"SELECT id FROM tax_rate WHERE name = '{name}'")
        if rows:
            _track_entity("tax_rate", rows[0]["id"])

    def test_create_invalid_rate(self, test_admin_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/tax-rates", json={
            "name": "Bad", "rate": 150, "is_default": False,
        }, headers=test_admin_headers, timeout=10)
        assert resp.status_code == 422

    def test_list(self, test_admin_headers: dict, session_suffix: str):
        _create_rate(test_admin_headers, session_suffix, "lst")
        resp = httpx.get(f"{SERVER_URL}/api/tax-rates", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "tax_rates" in data
        assert "total" in data

    def test_update(self, test_admin_headers: dict, session_suffix: str):
        rate_id = _create_rate(test_admin_headers, session_suffix, "upd")
        saved = save_default_tax_rate(test_admin_headers)
        try:
            resp = httpx.put(f"{SERVER_URL}/api/tax-rates/{rate_id}", json={
                "name": "Updated Tax", "rate": 9.0, "is_default": True,
            }, headers=test_admin_headers, timeout=10)
            assert_ok(resp)
        finally:
            restore_default_tax_rate(test_admin_headers, saved)

    def test_update_nonexistent(self, test_admin_headers: dict):
        resp = httpx.put(f"{SERVER_URL}/api/tax-rates/nonexistent-999", json={
            "name": "Nope", "rate": 5.0, "is_default": False,
        }, headers=test_admin_headers, timeout=10)
        assert resp.status_code < 500

    def test_delete(self, test_admin_headers: dict, session_suffix: str):
        rate_id = _create_rate(test_admin_headers, session_suffix, "del")
        resp = httpx.delete(f"{SERVER_URL}/api/tax-rates/{rate_id}", headers=test_admin_headers, timeout=10)
        assert_ok(resp)

    def test_delete_nonexistent(self, test_admin_headers: dict):
        resp = httpx.delete(f"{SERVER_URL}/api/tax-rates/nonexistent-999", headers=test_admin_headers, timeout=10)
        assert resp.status_code < 500

    def test_set_default(self, test_admin_headers: dict, session_suffix: str):
        rate_id = _create_rate(test_admin_headers, session_suffix, "def")
        saved = save_default_tax_rate(test_admin_headers)
        try:
            resp = httpx.put(f"{SERVER_URL}/api/tax-rates/{rate_id}", json={
                "name": "Default Tax", "rate": 6.0, "is_default": True,
            }, headers=test_admin_headers, timeout=10)
            assert_ok(resp)
        finally:
            restore_default_tax_rate(test_admin_headers, saved)


class TestTaxRateErrors:
    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/tax-rates", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post("/api/tax-rates", json={"name": "X", "rate": 5.0, "is_default": False}, timeout=10)
        assert resp.status_code in (401, 403)
