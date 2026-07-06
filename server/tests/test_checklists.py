"""Checklist template CRUD tests."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok, unique_suffix, _stdb_sql


def _create_template(auth_headers: dict, suffix: str = "") -> str:
    """Create a checklist template and return its ID.

    Uses unique name and STDB SQL lookup for isolation.
    """
    suf = suffix or unique_suffix()
    name = f"Checklist-{suf}"
    resp = httpx.post(f"{SERVER_URL}/api/checklist-templates", json={
        "name": name,
        "description": f"Test checklist {suf}",
        "items": [{"label": "Step 1", "order": 1}, {"label": "Step 2", "order": 2}],
    }, headers=auth_headers, timeout=10)
    assert_ok(resp)

    rows = _stdb_sql(f"SELECT id FROM checklist_template WHERE name = '{name}'")
    assert len(rows) >= 1, f"Template not found with name '{name}'"
    return rows[0]["id"]


class TestChecklistCRUD:
    def test_create(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/checklist-templates", json={
            "name": "Inspection Checklist",
            "description": "Standard equipment inspection steps",
            "items": [
                {"label": "Check power", "order": 1},
                {"label": "Test connectivity", "order": 2},
                {"label": "Verify output", "order": 3},
            ],
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_create_minimal(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/checklist-templates", json={
            "name": "Minimal Checklist", "description": "", "items": [],
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_create_missing_name(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/checklist-templates", json={}, headers=auth_headers, timeout=10)
        assert resp.status_code == 422

    def test_list(self, auth_headers: dict):
        _create_template(auth_headers, "lst")
        resp = httpx.get(f"{SERVER_URL}/api/checklist-templates", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "templates" in data
        assert "total" in data

    def test_update(self, auth_headers: dict):
        tid = _create_template(auth_headers, "upd")
        resp = httpx.put(f"{SERVER_URL}/api/checklist-templates/{tid}", json={
            "name": "Updated Checklist",
            "description": "Revised steps",
            "items": [{"label": "New step 1", "order": 1}],
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_update_nonexistent(self, auth_headers: dict):
        resp = httpx.put(f"{SERVER_URL}/api/checklist-templates/nonexistent-999", json={
            "name": "Nope", "description": "", "items": [],
        }, headers=auth_headers, timeout=10)
        assert resp.status_code < 500

    def test_delete(self, auth_headers: dict):
        tid = _create_template(auth_headers, "del")
        resp = httpx.delete(f"{SERVER_URL}/api/checklist-templates/{tid}", headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_delete_nonexistent(self, auth_headers: dict):
        resp = httpx.delete(f"{SERVER_URL}/api/checklist-templates/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code < 500


class TestChecklistErrors:
    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/checklist-templates", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post("/api/checklist-templates", json={"name": "X", "description": "", "items": []}, timeout=10)
        assert resp.status_code in (401, 403)
