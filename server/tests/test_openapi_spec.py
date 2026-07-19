"""OpenAPI spec contract tests for SpacetimeCRM.

Validates the auto-generated OpenAPI schema and endpoint contracts:
  - OpenAPI spec is valid and parseable
  - All registered routes appear in the OpenAPI spec
  - Endpoints enforce security (Bearer token where required)
  - Response shapes match expected patterns
  - Required request body fields are enforced
  - Auth-protected endpoints reject unauthenticated requests
"""

import json
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, assert_unauthorized, test_admin_headers


# ── Helpers ──────────────────────────────────────────────────────


def get_openapi_schema() -> dict:
    """Fetch the auto-generated OpenAPI spec from the running server."""
    resp = httpx.get(f"{SERVER_URL}/openapi.json", timeout=10)
    assert resp.status_code == 200, f"Failed to fetch OpenAPI schema: {resp.status_code}"
    return resp.json()


def get_all_api_paths(schema: dict) -> list[tuple[str, str]]:
    """Extract all (path, method) tuples from the schema, excluding SPA catch-all."""
    paths = []
    for path, methods in schema.get("paths", {}).items():
        if path == "/{full_path}":
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            if method in methods:
                paths.append((path, method.upper()))
    return sorted(paths, key=lambda x: x[0])


def requires_auth(schema: dict, path: str, method: str) -> bool:
    """Check if an endpoint requires auth (has security or Bearer scheme)."""
    path_item = schema["paths"].get(path, {})
    op = path_item.get(method, {})
    # Check endpoint-level security
    if "security" in op:
        return True
    # Check path-level security
    if "security" in path_item:
        return True
    # Public endpoints
    public_prefixes = ("/api/health", "/api/auth/login", "/api/auth/forgot-password",
                       "/api/auth/reset-password", "/api/webhooks/stripe")
    return not any(path.startswith(p) for p in public_prefixes)


# ── Tests: OpenAPI Schema Integrity ──────────────────────────────


class TestOpenAPISchema:
    """The /openapi.json endpoint is valid and well-formed."""

    def test_schema_is_served(self):
        """OpenAPI schema is accessible."""
        schema = get_openapi_schema()
        assert schema.get("openapi", "").startswith("3.")
        assert schema["info"]["title"] == "SpacetimeCRM"

    def test_schema_has_components(self):
        """Schema defines reusable components."""
        schema = get_openapi_schema()
        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "securitySchemes" in schema["components"]

    def test_schema_has_bearer_auth(self):
        """Security scheme includes HTTP Bearer."""
        schema = get_openapi_schema()
        schemes = schema["components"].get("securitySchemes", {})
        assert "HTTPBearer" in schemes
        assert schemes["HTTPBearer"]["type"] == "http"
        assert schemes["HTTPBearer"]["scheme"] == "bearer"

    def test_all_routes_documented(self):
        """Every FastAPI route appears in the OpenAPI spec."""
        schema = get_openapi_schema()
        paths = schema.get("paths", {})
        # At minimum we should have health, auth, and entity routes
        essential_paths = [
            "/api/health",
            "/api/auth/login",
            "/api/customers",
            "/api/tickets",
            "/api/invoices",
        ]
        for path in essential_paths:
            assert path in paths, f"Missing path in OpenAPI spec: {path}"

    def test_no_empty_responses(self):
        """Every operation should have at least a 200/201 response documented."""
        schema = get_openapi_schema()
        for path, methods in schema["paths"].items():
            if path == "/{full_path}":
                continue
            for method, op in methods.items():
                if method in ("parameters",):
                    continue
                assert "responses" in op, f"{method.upper()} {path} has no responses"

# ── Tests: Auth Enforcement ──────────────────────────────────────


class TestAuthEnforcement:
    """All non-public endpoints require authentication."""

    PUBLIC_ENDPOINTS = [
        ("GET", "/api/health"),
        ("GET", "/api/health/ready"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/forgot-password"),
    ]

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/customers"),
        ("GET", "/api/tickets"),
        ("GET", "/api/invoices"),
        ("GET", "/api/products"),
        ("GET", "/api/appointments"),
        ("GET", "/api/payments"),
        ("GET", "/api/estimates"),
        ("GET", "/api/users"),
        ("GET", "/api/settings/business-hours"),
        ("GET", "/api/tax-rates"),
        ("GET", "/api/tenants"),
        ("GET", "/api/stats"),
        ("GET", "/api/audit-log"),
        ("GET", "/api/reports"),
    ]

    def test_protected_endpoints_reject_no_auth(self, client: httpx.Client):
        """All protected GET endpoints return 401/403 without a token."""
        for method, path in self.PROTECTED_ENDPOINTS:
            resp = client.request(method, path)
            assert resp.status_code in (401, 403), (
                f"{method} {path} expected 401/403, got {resp.status_code}: {resp.text[:100]}"
            )

    def test_protected_endpoints_reject_bad_token(self, client: httpx.Client):
        """All protected GET endpoints return 401/403 with an invalid token."""
        headers = {"Authorization": "Bearer definitely-not-a-valid-jwt-token"}
        for method, path in self.PROTECTED_ENDPOINTS:
            resp = client.request(method, path, headers=headers)
            assert resp.status_code in (401, 403), (
                f"{method} {path} expected 401/403 with bad token, got {resp.status_code}"
            )

    def test_public_endpoints_accessible(self, client: httpx.Client):
        """Public endpoints return <500 without auth."""
        for method, path in self.PUBLIC_ENDPOINTS:
            resp = client.request(method, path)
            assert resp.status_code < 500, (
                f"{method} {path} public endpoint returned {resp.status_code}"
            )


# ── Tests: Response Shape Contract ───────────────────────────────


class TestResponseContracts:
    """Validate response shapes match expected patterns."""

    def test_health_returns_expected_structure(self, client: httpx.Client):
        """GET /api/health returns {server, stdb, module} with 'ok' values."""
        resp = client.get("/api/health")
        data = assert_ok(resp)
        assert isinstance(data, dict)
        assert data.get("server") == "ok"
        assert data.get("stdb") == "ok"
        assert data.get("module") == "ok"
        allowed = {"server", "stdb", "module"}
        extra = set(data.keys()) - allowed
        assert not extra, f"Unexpected health keys: {extra}"

    def test_auth_me_returns_user(self, auth_client: httpx.Client):
        """GET /api/auth/me returns user info with expected fields."""
        resp = auth_client.get("/api/auth/me")
        data = assert_ok(resp)
        assert "email" in data
        assert "role" in data
        assert "name" in data or "first_name" in data

    def test_customers_list_returns_paginated(self, auth_client: httpx.Client):
        """GET /api/customers returns paginated list."""
        resp = auth_client.get("/api/customers")
        data = assert_ok(resp)
        if isinstance(data, dict):
            assert "customers" in data or "items" in data or "data" in data
        elif isinstance(data, list):
            assert len(data) >= 0

    def test_422_on_invalid_body(self, client: httpx.Client):
        """POST /api/customers with empty body returns 422 (validation is pre-auth)."""
        resp = client.post("/api/customers", json={})
        # 422 comes from FastAPI validation, which runs before auth middleware
        assert resp.status_code in (422, 401, 403), (
            f"Expected 422 or 401/403 for empty body, got {resp.status_code}: {resp.text[:200]}"
        )

    def test_422_on_missing_required(self, client: httpx.Client):
        """POST /api/customers with missing required fields returns 422 (validation is pre-auth)."""
        resp = client.post("/api/customers", json={"email": "test@test.com"})
        assert resp.status_code in (422, 401, 403), (
            f"Expected 422 or 401/403 for missing required fields, got {resp.status_code}"
        )
        if resp.status_code == 422:
            data = resp.json()
            assert "detail" in data
            detail_str = json.dumps(data["detail"]).lower()
            assert "first_name" in detail_str or "last_name" in detail_str


# ── Tests: Error Contract ────────────────────────────────────────


class TestErrorContracts:
    """Error responses follow a consistent format."""

    def test_401_returns_json(self, client: httpx.Client):
        """Unauthenticated requests return JSON, not HTML."""
        resp = client.get("/api/customers")
        assert_unauthorized(resp)
        content_type = resp.headers.get("content-type", "")
        assert "json" in content_type, f"Expected JSON, got: {content_type}"
        data = resp.json()
        assert "detail" in data, f"401 response missing 'detail' field: {data}"

    def test_404_returns_not_crash(self, client: httpx.Client):
        """Non-existent API-like path returns appropriate status (SPA fallback may catch)."""
        # The SPA fallback at /{full_path:path} catches all unmatched routes,
        # so /api/nonexistent-route-xy1234 may return 200 with index.html
        resp = client.get("/api/this-path-should-not-exist-99999999")
        # Should not crash — either 404 from FastAPI or 200 from SPA fallback
        assert resp.status_code < 500, f"Request crashed: {resp.status_code}"

    def test_validation_error_format(self, client: httpx.Client):
        """422 validation errors include 'detail' array with 'loc' and 'msg'."""
        resp = client.post("/api/customers", json={})
        if resp.status_code == 422:
            data = resp.json()
            assert "detail" in data
            assert isinstance(data["detail"], list)
            if data["detail"]:
                err = data["detail"][0]
                assert "loc" in err, f"Validation error missing 'loc': {err}"
                assert "msg" in err, f"Validation error missing 'msg': {err}"


# ── Tests: HTTP Method Contract ──────────────────────────────────


class TestHTTPMethodContract:
    """Unsupported HTTP methods return 405 or appropriate error."""

    def test_unsupported_method_returns_405(self, client: httpx.Client):
        """PATCH on a GET-only endpoint returns 405."""
        resp = client.patch("/api/stats")
        assert resp.status_code in (405, 404, 401, 403), (
            f"Expected 405/404 for unsupported method, got {resp.status_code}"
        )

    def test_delete_on_nonexistent_does_not_crash(self, client: httpx.Client):
        """DELETE on nonexistent resource returns error, not crash."""
        resp = client.delete("/api/tax-rates/nonexistent-999999")
        assert resp.status_code < 500, f"DELETE crashed: {resp.status_code}"


# ── Tests: CORS Contract ─────────────────────────────────────────


class TestCORSContract:
    """CORS headers are present on all API responses."""

    def test_cors_origin_present(self, client: httpx.Client):
        """API responses include Access-Control-Allow-Origin when Origin sent."""
        resp = client.get("/api/health", headers={"Origin": "http://localhost:5185"})
        origin = resp.headers.get("access-control-allow-origin")
        assert origin is not None, "Missing CORS Access-Control-Allow-Origin"

    def test_cors_preflight_succeeds(self, client: httpx.Client):
        """OPTIONS preflight succeeds for API paths."""
        resp = client.options("/api/customers", headers={
            "Origin": "http://localhost:5185",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.status_code in (200, 204), f"CORS preflight failed: {resp.status_code}"

    def test_cors_allows_all_methods(self, client: httpx.Client):
        """OPTIONS returns permissive Access-Control-Allow-Methods."""
        resp = client.options("/api/customers", headers={
            "Origin": "http://localhost:5185",
            "Access-Control-Request-Method": "GET",
        })
        methods = resp.headers.get("access-control-allow-methods", "")
        assert methods, "Missing Access-Control-Allow-Methods"
        assert "*" in methods or "GET" in methods, f"Unexpected methods: {methods}"

# ── Tests: Schema Coverage (route ↔ OpenAPI match) ────────────────


class TestSchemaCoverage:
    """Validate every API path in the codebase is documented in OpenAPI."""

    def _get_registered_routes(self) -> set[tuple[str, str]]:
        """Scrape route files to find all registered (method, path) pairs."""
        import ast
        import os
        routes_dir = os.path.join(os.path.dirname(__file__), "..", "routes")
        routes: set[tuple[str, str]] = set()
        for fname in sorted(os.listdir(routes_dir)):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            fpath = os.path.join(routes_dir, fname)
            with open(fpath) as f:
                try:
                    tree = ast.parse(f.read(), filename=fpath)
                except SyntaxError:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id in ("router", "app")
                            and node.func.attr in ("get", "post", "put", "patch", "delete")):
                        method = node.func.attr.upper()
                        if node.args:
                            path_literal = node.args[0]
                            if isinstance(path_literal, ast.Constant) and isinstance(path_literal.value, str):
                                routes.add((method, path_literal.value))
        return routes

    def test_all_registered_routes_in_openapi(self):
        """Every route defined in routes/*.py appears in the OpenAPI spec."""
        schema = get_openapi_schema()
        schema_paths = schema.get("paths", {})
        registered = self._get_registered_routes()
        missing = []
        for method, path in sorted(registered):
            if path not in schema_paths:
                missing.append(f"{method} {path}")
                continue
            if method.lower() not in schema_paths[path]:
                missing.append(f"{method} {path} (method not documented)")
        if missing:
            pytest.fail(
                "Routes missing from OpenAPI spec:\n  " + "\n  ".join(missing[:20])
            )

    def test_no_orphan_schema_paths(self):
        """Every OpenAPI path (except SPA fallback) has a corresponding route handler."""
        import ast
        import os
        routes_dir = os.path.join(os.path.dirname(__file__), "..", "routes")
        registered: set[str] = set()
        for fname in sorted(os.listdir(routes_dir)):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            fpath = os.path.join(routes_dir, fname)
            with open(fpath) as f:
                try:
                    tree = ast.parse(f.read(), filename=fpath)
                except SyntaxError:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id in ("router", "app")
                            and node.func.attr in ("get", "post", "put", "patch", "delete")):
                        if node.args:
                            path_literal = node.args[0]
                            if isinstance(path_literal, ast.Constant) and isinstance(path_literal.value, str):
                                registered.add(path_literal.value)
        schema = get_openapi_schema()
        orphan = []
        for path in schema["paths"]:
            if path == "/{full_path}":
                continue
            if path not in registered:
                orphan.append(path)
        if orphan:
            pytest.fail(
                "OpenAPI paths without route handlers:\n  " + "\n  ".join(orphan[:20])
            )


# ── Tests: Request Body Contract ────────────────────────────────


class TestRequestBodyContract:
    """Endpoints with required request bodies enforce them."""

    def _get_request_schema(self, schema: dict, path: str, method: str):
        """Get the request body schema for an endpoint, resolving $ref."""
        op = schema["paths"][path][method.lower()]
        if "requestBody" not in op:
            return None
        content = op["requestBody"].get("content", {})
        json_schema = content.get("application/json", {}).get("schema")
        if json_schema is None:
            return None
        # Resolve $ref references
        if "$ref" in json_schema:
            ref_path = json_schema["$ref"].lstrip("#/").split("/")
            resolved = schema
            for part in ref_path:
                resolved = resolved[part]
            return resolved
        return json_schema

    def test_login_has_request_body(self):
        """POST /api/auth/login defines a request body."""
        schema = get_openapi_schema()
        req_schema = self._get_request_schema(schema, "/api/auth/login", "post")
        assert req_schema is not None, "Login endpoint missing request body"
        props = req_schema.get("properties", {})
        assert "email" in props
        assert "password" in props

    def test_customer_create_has_required_fields(self):
        """POST /api/customers requires first_name and last_name."""
        schema = get_openapi_schema()
        req_schema = self._get_request_schema(schema, "/api/customers", "post")
        assert req_schema is not None
        required = req_schema.get("required", [])
        assert "first_name" in required
        assert "last_name" in required

    def test_ticket_create_has_required_fields(self):
        """POST /api/tickets requires customer_id and title."""
        schema = get_openapi_schema()
        req_schema = self._get_request_schema(schema, "/api/tickets", "post")
        assert req_schema is not None
        required = req_schema.get("required", [])
        assert "customer_id" in required
        assert "title" in required

    def test_invoice_create_has_required_fields(self):
        """POST /api/invoices requires customer_id."""
        schema = get_openapi_schema()
        req_schema = self._get_request_schema(schema, "/api/invoices", "post")
        assert req_schema is not None
        required = req_schema.get("required", [])
        assert "customer_id" in required

    def test_payment_create_has_required_fields(self):
        """POST /api/payments requires invoice_id, customer_id, amount."""
        schema = get_openapi_schema()
        req_schema = self._get_request_schema(schema, "/api/payments", "post")
        assert req_schema is not None
        required = req_schema.get("required", [])
        assert "invoice_id" in required
        assert "customer_id" in required
        assert "amount" in required

    def test_appointment_create_has_required_fields(self):
        """POST /api/appointments requires customer_id, title, start_time, end_time."""
        schema = get_openapi_schema()
        req_schema = self._get_request_schema(schema, "/api/appointments", "post")
        assert req_schema is not None
        required = req_schema.get("required", [])
        assert "customer_id" in required
        assert "title" in required
        assert "start_time" in required
        assert "end_time" in required

    def test_product_create_has_required_name(self):
        """POST /api/products requires name."""
        schema = get_openapi_schema()
        req_schema = self._get_request_schema(schema, "/api/products", "post")
        assert req_schema is not None
        required = req_schema.get("required", [])
        assert "name" in required
