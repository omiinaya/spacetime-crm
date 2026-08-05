"""Checklist template CRUD tests."""

import httpx

from .conftest import (
    SERVER_URL,
    _stdb_sql,
    _track_entity,
    assert_ok,
    unique_suffix,
)


def _create_template(test_admin_headers: dict, session_suffix: str = "", suffix: str = "") -> str:
    """Create a checklist template and return its ID.

    Uses unique name and STDB SQL lookup for isolation.
    session_suffix ensures cleanup by suffix works across sessions.
    """
    suf = suffix or unique_suffix()
    name = f"Checklist-{session_suffix}-{suf}"
    resp = httpx.post(
        f"{SERVER_URL}/api/checklist-templates",
        json={
            "name": name,
            "description": f"Test checklist {suf}",
            "items": [{"label": "Step 1", "order": 1}, {"label": "Step 2", "order": 2}],
        },
        headers=test_admin_headers,
        timeout=10,
    )
    assert_ok(resp)

    result = _stdb_sql(f"SELECT id FROM checklist_templates WHERE name = '{name}'")
    assert len(result) == 1, f"Expected 1 table result for checklist '{name}'"
    table = result[0]
    assert table.get("rows") and len(table["rows"]) >= 1, f"Template not found with name '{name}'"
    tid = table["rows"][0][0]  # id is first (and only) column
    _track_entity("checklist_template", tid)
    return tid


class TestChecklistCRUD:
    def test_create(self, test_admin_headers: dict):
        from .conftest import unique_suffix

        name = f"Inspection Checklist {unique_suffix()}"
        resp = httpx.post(
            f"{SERVER_URL}/api/checklist-templates",
            json={
                "name": name,
                "description": "Standard equipment inspection steps",
                "items": [
                    {"label": "Check power", "order": 1},
                    {"label": "Test connectivity", "order": 2},
                    {"label": "Verify output", "order": 3},
                ],
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_create_minimal(self, test_admin_headers: dict):
        from .conftest import unique_suffix

        name = f"Minimal Checklist {unique_suffix()}"
        resp = httpx.post(
            f"{SERVER_URL}/api/checklist-templates",
            json={
                "name": name,
                "description": "",
                "items": [],
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_create_missing_name(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/checklist-templates",
            json={},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_list(self, test_admin_headers: dict, session_suffix: str):
        _create_template(test_admin_headers, session_suffix, "lst")
        resp = httpx.get(
            f"{SERVER_URL}/api/checklist-templates",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "templates" in data
        assert "total" in data

    def test_update(self, test_admin_headers: dict, session_suffix: str):
        tid = _create_template(test_admin_headers, session_suffix, "upd")
        resp = httpx.put(
            f"{SERVER_URL}/api/checklist-templates/{tid}",
            json={
                "name": "Updated Checklist",
                "description": "Revised steps",
                "items": [{"label": "New step 1", "order": 1}],
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_update_nonexistent(self, test_admin_headers: dict):
        resp = httpx.put(
            f"{SERVER_URL}/api/checklist-templates/nonexistent-999",
            json={
                "name": "Nope",
                "description": "",
                "items": [],
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500

    def test_delete(self, test_admin_headers: dict, session_suffix: str):
        tid = _create_template(test_admin_headers, session_suffix, "del")
        resp = httpx.delete(
            f"{SERVER_URL}/api/checklist-templates/{tid}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_delete_nonexistent(self, test_admin_headers: dict):
        resp = httpx.delete(
            f"{SERVER_URL}/api/checklist-templates/nonexistent-999",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500


class TestChecklistErrors:
    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/checklist-templates", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post(
            "/api/checklist-templates",
            json={"name": "X", "description": "", "items": []},
            timeout=10,
        )
        assert resp.status_code in (401, 403)
