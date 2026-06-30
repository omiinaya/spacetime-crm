"""Custom fields routes — definitions CRUD, values get/set."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok


def _create_field(auth_headers: dict, suffix: str = "") -> dict:
    """Create a custom field definition and return full response."""
    ts = int(__import__('time').time())
    resp = httpx.post(
        f"{SERVER_URL}/api/custom-field-definitions",
        json={
            "entity_type": "customer",
            "label": f"Test Field {suffix or 'A'}-{ts}",
            "field_type": "text",
            "options": [],
            "sort_order": 0,
            "required": False,
            "active": True,
        },
        headers=auth_headers, timeout=10,
    )
    data = assert_ok(resp)
    assert "id" in data
    return data


class TestCustomFieldDefinitions:
    """Custom field definition CRUD."""

    def test_create(self, auth_headers: dict):
        data = _create_field(auth_headers, "create")
        assert data.get("id", ""), f"Expected field ID in response: {data}"

    def test_create_invalid_entity_type(self, auth_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/custom-field-definitions",
            json={"entity_type": "invalid_type", "label": "Bad", "field_type": "text"},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422

    def test_create_invalid_field_type(self, auth_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/custom-field-definitions",
            json={"entity_type": "customer", "label": "Bad", "field_type": "binary"},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422

    def test_list(self, auth_headers: dict):
        _create_field(auth_headers, "list")
        resp = httpx.get(f"{SERVER_URL}/api/custom-field-definitions", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "custom_fields" in data
        assert "total" in data

    def test_update(self, auth_headers: dict):
        data = _create_field(auth_headers, "update")
        field_id = data["id"]
        resp = httpx.put(
            f"{SERVER_URL}/api/custom-field-definitions/{field_id}",
            json={
                "entity_type": "customer",
                "label": "Updated Field",
                "field_type": "number",
                "options": [],
                "sort_order": 1,
                "required": True,
                "active": True,
            },
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_delete(self, auth_headers: dict):
        data = _create_field(auth_headers, "delete")
        field_id = data["id"]
        resp = httpx.delete(f"{SERVER_URL}/api/custom-field-definitions/{field_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_delete_nonexistent(self, auth_headers: dict):
        resp = httpx.delete(f"{SERVER_URL}/api/custom-field-definitions/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code < 500


class TestCustomFieldValues:
    """Custom field values get/set on entities."""

    def test_get_values_empty(self, auth_headers: dict):
        """Get values for a non-existent entity — should return empty array."""
        entity_id = f"entity-empty-{int(__import__('time').time())}"
        resp = httpx.get(f"{SERVER_URL}/api/custom-field-values/{entity_id}", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert data.get("values") == []

    def test_set_and_get_values(self, auth_headers: dict, admin_user: dict):
        # Create a field
        data = _create_field(auth_headers, "vals")
        field_id = data["id"]

        # Create a customer entity to attach values to
        email = f"field-test-{int(__import__('time').time())}@example.com"
        httpx.post(f"{SERVER_URL}/api/customers", json={
            "first_name": "Field", "last_name": "Test", "email": email, "phone": "555-0000",
        }, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/customers", params={"search": email}, headers=auth_headers, timeout=10)
        items = r.json().get("customers", [])
        assert items, "Customer not created"
        entity_id = items[0]["id"]

        # Set a custom field value
        resp = httpx.put(
            f"{SERVER_URL}/api/custom-field-values/{entity_id}",
            json={"values": {field_id: "Hello World"}},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Read it back
        resp2 = httpx.get(f"{SERVER_URL}/api/custom-field-values/{entity_id}", headers=auth_headers, timeout=10)
        data2 = assert_ok(resp2)
        values = data2.get("values", [])
        assert len(values) >= 1, f"Expected at least 1 value, got: {values}"
        # Find our field value
        for v in values:
            if v.get("field_id") == field_id:
                assert str(v.get("value", "")) == "Hello World"
                break
        else:
            assert False, f"Field {field_id} not found in values: {values}"

    def test_set_values_invalid_entity(self, auth_headers: dict):
        """Set values on nonexistent entity — should still work (STDB allows it)."""
        entity_id = f"entity-nonexistent-{int(__import__('time').time())}"
        data = _create_field(auth_headers, "inv")
        resp = httpx.put(
            f"{SERVER_URL}/api/custom-field-values/{entity_id}",
            json={"values": {data["id"]: "orphaned value"}},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code < 500, resp.text[:200]


class TestCustomFieldErrors:
    """Auth enforcement for custom fields."""

    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/custom-field-definitions", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post("/api/custom-field-definitions", json={"entity_type": "customer", "label": "X", "field_type": "text"}, timeout=10)
        assert resp.status_code in (401, 403)
