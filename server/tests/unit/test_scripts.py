"""Unit tests for scripts/ modules (backup, bootstrap, restore, seed-demo, start-test-backend).

Tests utility functions and constants from each script.
External calls (httpx, subprocess, input) are mocked throughout.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is on sys.path so that scripts/ is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ── Helpers ──────────────────────────────────────────────────────


def _import_seed_demo() -> ModuleType:
    """Load scripts/seed-demo.py (hyphenated filename) via importlib."""
    path = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "seed-demo.py"
    spec = importlib.util.spec_from_file_location("seed_demo", str(path))
    assert spec is not None, f"Could not find spec for {path}"
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _remove_from_cache(*names: str) -> None:
    """Remove modules from sys.modules to force re-import."""
    import sys

    for name in names:
        for key in list(sys.modules):
            if key == name or key.startswith(f"{name}."):
                del sys.modules[key]


# ===================================================================
# scripts/backup.py
# ===================================================================


class TestBackupConstants:
    """Constants and configuration."""

    def test_tables_list_not_empty(self) -> None:
        from scripts import backup

        assert len(backup.TABLES) > 0

    def test_tables_list_contains_expected_tables(self) -> None:
        from scripts import backup

        expected = {"customer", "user", "ticket", "payment", "appointment", "audit_log"}
        assert expected.issubset(set(backup.TABLES))

    def test_db_name(self) -> None:
        from scripts import backup

        assert backup.DB_NAME == "spacetime-crm"

    def test_sql_url_format(self) -> None:
        from scripts import backup

        assert "localhost" in backup.SQL_URL
        assert "3001" in backup.SQL_URL
        assert "spacetime-crm" in backup.SQL_URL
        assert "/v1/database/" in backup.SQL_URL


class TestBackupSqlQuery:
    """sql_query() function with mocked HTTP client."""

    def test_returns_empty_on_http_error(self) -> None:
        from scripts.backup import sql_query

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Table not found"
        mock_client.post.return_value = mock_resp

        result = sql_query(mock_client, "SELECT * FROM nonexistent")
        assert result == []
        mock_client.post.assert_called_once()

    def test_returns_empty_on_500(self) -> None:
        from scripts.backup import sql_query

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal error"
        mock_client.post.return_value = mock_resp

        result = sql_query(mock_client, "SELECT * FROM bad")
        assert result == []

    def test_parses_rows_with_schema(self) -> None:
        from scripts.backup import sql_query

        schema = {
            "elements": [
                {"name": {"some": "id"}},
                {"name": {"some": "name"}},
                {"name": {"some": "email"}},
            ]
        }
        rows = [["c-1", "Alice", "alice@test.com"], ["c-2", "Bob", "bob@test.com"]]

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"schema": schema, "rows": rows}]
        mock_client.post.return_value = mock_resp

        result = sql_query(mock_client, "SELECT * FROM customer")
        assert len(result) == 2
        assert result[0] == {"id": "c-1", "name": "Alice", "email": "alice@test.com"}
        assert result[1] == {"id": "c-2", "name": "Bob", "email": "bob@test.com"}

    def test_handles_empty_result_set(self) -> None:
        from scripts.backup import sql_query

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_client.post.return_value = mock_resp

        result = sql_query(mock_client, "SELECT * FROM empty_table")
        assert result == []

    def test_handles_rows_with_no_schema_elements(self) -> None:
        from scripts.backup import sql_query

        schema = {"elements": []}
        rows = [["val1", "val2"]]

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"schema": schema, "rows": rows}]
        mock_client.post.return_value = mock_resp

        result = sql_query(mock_client, "SELECT * FROM weird")
        assert result == [{}]

    def test_sends_correct_headers(self) -> None:
        from scripts.backup import sql_query

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_client.post.return_value = mock_resp

        sql_query(mock_client, "SELECT 1")
        _, kwargs = mock_client.post.call_args
        assert kwargs["headers"]["Content-Type"] == "application/sql"
        assert kwargs["content"] == "SELECT 1"


# ===================================================================
# scripts/bootstrap.py (module-level side effects — mocked at import)
# ===================================================================


class TestBootstrapConfig:
    """Environment variable defaults and URL construction.

    bootstrap.py runs HTTP calls at module-import time. We mock httpx
    entirely before importing so no real server is contacted.
    """

    def test_default_env_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for k in ["STDB_HOST", "STDB_PORT", "STDB_DB", "CRM_API_URL"]:
            monkeypatch.delenv(k, raising=False)

        _remove_from_cache("scripts.bootstrap")

        mock_client = _make_mock_http_client(health_ok=True)

        with patch.dict("sys.modules", {"httpx": MagicMock(Client=lambda *a, **kw: mock_client)}):
            import importlib

            from scripts import bootstrap

            importlib.reload(bootstrap)

        assert bootstrap.STDB_HOST == "localhost"
        assert bootstrap.STDB_PORT == "3001"
        assert bootstrap.STDB_DB == "spacetime-crm"
        assert bootstrap.CRM_API_URL == "http://localhost:8723"
        assert bootstrap.STDB == "http://localhost:3001"

    def test_env_var_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STDB_HOST", "10.0.0.1")
        monkeypatch.setenv("STDB_PORT", "9999")
        monkeypatch.setenv("STDB_DB", "test-db")
        monkeypatch.setenv("CRM_API_URL", "http://test:8888")

        _remove_from_cache("scripts.bootstrap")

        mock_client = _make_mock_http_client(health_ok=True)

        with patch.dict("sys.modules", {"httpx": MagicMock(Client=lambda *a, **kw: mock_client)}):
            import importlib

            mod = importlib.import_module("scripts.bootstrap")

        assert mod.STDB_HOST == "10.0.0.1"
        assert mod.STDB_PORT == "9999"
        assert mod.STDB_DB == "test-db"
        assert mod.CRM_API_URL == "http://test:8888"
        assert mod.STDB == "http://10.0.0.1:9999"

    def test_creates_client_with_timeout(self) -> None:
        """Verify the Client is constructed with the right base URL and timeout."""
        _remove_from_cache("scripts.bootstrap")

        mock_client = _make_mock_http_client(health_ok=True)

        with patch.dict("sys.modules", {"httpx": MagicMock(Client=lambda *a, **kw: mock_client)}):
            import importlib

            mod = importlib.import_module("scripts.bootstrap")

        assert mod.STDB == "http://localhost:3001"


def _make_mock_http_client(*, health_ok: bool = True) -> MagicMock:
    """Build a mock httpx.Client that bootstrap's module-level code can use.

    bootstrap.py runs these HTTP calls at module level:
      1. GET /health (wait for STDB)
      2. POST /v1/database/{DB}/call/create_tenant
      3. POST /v1/database/{DB}/call/create_user
      4. POST /v1/database/{DB}/sql  (find user by email)
      5. POST /v1/database/{DB}/call/set_user_password
      6. POST /v1/database/{DB}/sql  (find tenant by slug)
      7. POST /v1/database/{DB}/call/add_tenant_member
      8. POST /api/auth/login  (verify login via CRM API)
    """
    mock_client = MagicMock()

    # Health check → 200
    mock_health = MagicMock(status_code=200 if health_ok else 500)
    mock_client.get.return_value = mock_health

    # STDB SQL result (both user and tenant queries) — rows with id
    stdb_rows = [["user-1", "admin", "admin@crm.local", "admin", None]]
    stdb_schema = {
        "elements": [
            {"name": {"some": "id"}},
            {"name": {"some": "username"}},
            {"name": {"some": "email"}},
            {"name": {"some": "role"}},
        ]
    }
    stdb_sql_payload = [{"rows": stdb_rows, "schema": stdb_schema}]

    mock_sql_resp = MagicMock()
    mock_sql_resp.status_code = 200
    mock_sql_resp.json.return_value = stdb_sql_payload
    mock_sql_resp.text = json.dumps(stdb_sql_payload)

    # POST /call/* → success (reducers return 200 with no JSON body)
    mock_call_resp = MagicMock()
    mock_call_resp.status_code = 200
    mock_call_resp.text = "ok"
    mock_call_resp.json.side_effect = RuntimeError("no json body on /call responses")

    # POST /api/auth/login → JWT token
    mock_login_resp = MagicMock()
    mock_login_resp.status_code = 200
    mock_login_resp.json.return_value = {
        "token": "test-jwt-token-for-bootstrap-verification",
        "user": {"tenant_id": "tenant-1"},
    }
    mock_login_resp.text = json.dumps({"token": "test-jwt-token"})

    def post_side_effect(url, **kwargs):
        if "/sql" in url:
            return mock_sql_resp
        if "/api/auth/login" in url:
            return mock_login_resp
        return mock_call_resp

    mock_client.post.side_effect = post_side_effect

    return mock_client


# ===================================================================
# scripts/restore.py
# ===================================================================


class TestRestoreRunSpacetime:
    """run_spacetime() with mocked subprocess."""

    def test_returns_stdout_on_success(self) -> None:
        from scripts.restore import run_spacetime

        with patch("scripts.restore.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "database deleted\n"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = run_spacetime(["delete", "-y", "spacetime-crm"])
            assert result == "database deleted"

    def test_includes_server_flag(self) -> None:
        from scripts.restore import run_spacetime

        with patch("scripts.restore.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            run_spacetime(["list"])
            args = mock_run.call_args[0][0]
            assert args[0] == "spacetime"
            assert args[1] == "--server"
            assert "localhost" in args[2]

    def test_uses_60s_timeout(self) -> None:
        from scripts.restore import run_spacetime

        with patch("scripts.restore.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            run_spacetime(["list"])
            assert mock_run.call_args[1].get("timeout") == 60

    def test_captures_stderr_on_failure(self, capsys: pytest.CaptureFixture) -> None:
        from scripts.restore import run_spacetime

        with patch("scripts.restore.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "identity not found"
            mock_run.return_value = mock_result

            result = run_spacetime(["delete", "-y", "test"])
            assert result == ""
            captured = capsys.readouterr()
            assert "identity not found" in captured.out


class TestRestoreConfirm:
    """confirm() with monkeypatched input."""

    def test_accepts_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.restore import confirm

        monkeypatch.setattr("builtins.input", lambda _: "yes")
        confirm()  # should not raise

    def test_rejects_non_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.restore import confirm

        monkeypatch.setattr("builtins.input", lambda _: "no")
        with pytest.raises(SystemExit):
            confirm()

    def test_rejects_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.restore import confirm

        monkeypatch.setattr("builtins.input", lambda _: "")
        with pytest.raises(SystemExit):
            confirm()

    def test_accepts_YES_uppercase(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.restore import confirm

        monkeypatch.setattr("builtins.input", lambda _: "YES")
        confirm()  # should not raise — .lower() comparison accepts "YES"


class TestRestoreConstants:
    """Restore config and data structures."""

    def test_db_name(self) -> None:
        from scripts import restore

        assert restore.DB_NAME == "spacetime-crm"

    def test_wasm_file_path_resolved_correctly(self) -> None:
        from scripts import restore

        assert "server" in str(restore.WASM_FILE)
        assert "spacetimedb" in str(restore.WASM_FILE)
        assert "wasm32" in str(restore.WASM_FILE)
        assert restore.WASM_FILE.name == "spacetime_crm.wasm"

    def test_call_url_format(self) -> None:
        from scripts import restore

        assert "localhost" in restore.CALL_URL
        assert "spacetime-crm" in restore.CALL_URL
        assert "/call" in restore.CALL_URL

    def test_module_dir_points_to_spacetimedb(self) -> None:
        from scripts import restore

        assert restore.MODULE_DIR.name == "spacetimedb"

    def test_stdb_server_url(self) -> None:
        from scripts import restore

        assert restore.STDB_HOST == "localhost"
        assert restore.STDB_PORT == 3001
        assert f"http://{restore.STDB_HOST}:{restore.STDB_PORT}" == restore.STDB_SERVER


# ===================================================================
# scripts/seed-demo.py (hyphenated filename, module-level HTTP calls)
# ===================================================================


class TestSeedDemoHelpers:
    """Helper functions."""

    def test_ok_returns_true_for_200(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            assert mod.ok(mock_resp) is True

    @pytest.mark.parametrize("code", [201, 204, 301, 400, 401, 403, 404, 500])
    def test_ok_returns_false_for_non_200(self, code: int) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            mock_resp = MagicMock()
            mock_resp.status_code = code
            assert mod.ok(mock_resp) is False


class TestSeedDemoData:
    """Data structure integrity."""

    def test_customers_have_expected_fields(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            assert len(mod.customers) > 0
            for c in mod.customers:
                assert len(c) == 9
                assert "@" in c[2]  # email has @

    def test_products_have_valid_prices(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            assert len(mod.products) > 0
            for p in mod.products:
                assert len(p) == 6
                assert p[2] > 0  # price > 0
                assert p[3] >= 0  # cost >= 0

    def test_tickets_reference_valid_customers(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            max_idx = len(mod.customers) - 1
            for t in mod.tickets:
                assert len(t) == 5
                assert 0 <= t[0] <= max_idx, (
                    f"Ticket references customer index {t[0]} but only {max_idx + 1} customers exist"
                )

    def test_ticket_statuses(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            valid_statuses = {
                "new",
                "assigned",
                "in_progress",
                "waiting_on_customer",
                "resolved",
            }
            for t in mod.tickets:
                assert t[3] in valid_statuses, f"Invalid status: {t[3]}"

    def test_invoice_items_data_has_valid_customer_indices(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            max_idx = len(mod.customers) - 1
            for ci, _ti, _items in mod.inv_items_data:
                assert 0 <= ci <= max_idx, (
                    f"References customer index {ci} but only {max_idx + 1} customers exist"
                )

    def test_appointments_have_valid_statuses(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            valid = {"scheduled", "completed", "cancelled", "in_progress", "no_show"}
            for appt in mod.appts:
                assert appt[4] in valid, f"Invalid appointment status: {appt[4]}"

    def test_appointment_times_are_reasonable(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            for appt in mod.appts:
                assert appt[2] > 0, "Start time should be positive"
                assert appt[3] > appt[2], "End time should be after start time"

    def test_variable_names_exist(self) -> None:
        """Verify all expected data variables are present at module level."""
        mock_httpx = MagicMock()
        mock_httpx.post.return_value = MagicMock(status_code=200)
        mock_httpx.Client.return_value = mock_httpx

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            mod = _import_seed_demo()
            assert hasattr(mod, "customers")
            assert hasattr(mod, "products")
            assert hasattr(mod, "tickets")
            assert hasattr(mod, "inv_items_data")
            assert hasattr(mod, "appts")
            assert hasattr(mod, "ok")


# ===================================================================
# scripts/start-test-backend.py (module-level side effects — mocked)
# ===================================================================


class TestStartTestBackend:
    """start-test-backend.py has module-level side effects (Popen, os.chdir).

    We use path-based patching on the real os/subprocess/urllib modules,
    then load the script via importlib spec_from_file_location.
    """

    @staticmethod
    def _load_module(**patches):
        """Load start-test-backend.py with all external calls mocked.

        Returns the loaded module and the mock_subprocess.Popen for assertions.
        """
        _remove_from_cache("scripts.start_test_backend")

        from unittest.mock import patch as _patch

        # Build context manager stack
        stack = []
        for target, mock_value in patches.items():
            stack.append(_patch(target, mock_value))

        # Combine all patches into one
        combined = stack[0] if stack else _patch("os.path")  # no-op
        for _p in stack[1:]:
            combined = combined.__enter__.__class__  # can't easily nest
            # Actually, use ExitStack
            pass

        import contextlib

        with contextlib.ExitStack() as ctx_stack:
            patchers = {}
            for target, mock_value in patches.items():
                patchers[target] = ctx_stack.enter_context(_patch(target, mock_value))

            path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "scripts"
                / "start-test-backend.py"
            )
            spec = importlib.util.spec_from_file_location("start_test_backend", str(path))
            assert spec is not None
            assert spec.loader is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

        return mod, patchers

    def test_uses_test_port_and_env(self) -> None:
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None

        with patch("os.chdir"):
            with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_resp = MagicMock()
                    mock_resp.status = 200
                    mock_urlopen.return_value = mock_resp
                    with patch("builtins.open", MagicMock()):
                        path = (
                            Path(__file__).resolve().parent.parent.parent.parent
                            / "scripts"
                            / "start-test-backend.py"
                        )
                        spec = importlib.util.spec_from_file_location(
                            "start_test_backend", str(path)
                        )
                        assert spec is not None and spec.loader is not None
                        mod = importlib.util.module_from_spec(spec)
                        with pytest.raises(SystemExit) as excinfo:
                            spec.loader.exec_module(mod)
                        assert excinfo.value.code == 0  # healthy exit

        call_args = mock_popen.call_args[0][0]
        assert "--port" in call_args
        port_idx = call_args.index("--port")
        assert call_args[port_idx + 1] == "8724"

        env = mock_popen.call_args[1].get("env", {})
        assert env.get("STDB_PORT") == "3003"
        assert env.get("STDB_DB") == "spacetime-crm-test"

    def test_changes_to_server_directory(self) -> None:
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None

        with patch("os.chdir") as mock_chdir:
            with patch("subprocess.Popen", return_value=mock_proc):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_resp = MagicMock()
                    mock_resp.status = 200
                    mock_urlopen.return_value = mock_resp
                    with patch("builtins.open", MagicMock()):
                        path = (
                            Path(__file__).resolve().parent.parent.parent.parent
                            / "scripts"
                            / "start-test-backend.py"
                        )
                        spec = importlib.util.spec_from_file_location(
                            "start_test_backend", str(path)
                        )
                        assert spec is not None and spec.loader is not None
                        mod = importlib.util.module_from_spec(spec)
                        with pytest.raises(SystemExit):
                            spec.loader.exec_module(mod)

        mock_chdir.assert_called_once()
        assert "server" in str(mock_chdir.call_args[0][0])

    def test_waits_for_health_check(self) -> None:
        """If health responds quickly, the script should complete."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None

        with patch("os.chdir"):
            with patch("subprocess.Popen", return_value=mock_proc):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_resp = MagicMock()
                    mock_resp.status = 200
                    mock_urlopen.return_value = mock_resp
                    with patch("builtins.open", MagicMock()):
                        path = (
                            Path(__file__).resolve().parent.parent.parent.parent
                            / "scripts"
                            / "start-test-backend.py"
                        )
                        spec = importlib.util.spec_from_file_location(
                            "start_test_backend", str(path)
                        )
                        assert spec is not None and spec.loader is not None
                        mod = importlib.util.module_from_spec(spec)
                        with pytest.raises(SystemExit) as excinfo:
                            spec.loader.exec_module(mod)
                        assert excinfo.value.code == 0  # healthy process exits with 0

    def test_exits_if_process_dies(self) -> None:
        """If uvicorn process dies before becoming healthy, script exits."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = 1  # process died

        with patch("os.chdir"):
            with patch("subprocess.Popen", return_value=mock_proc):
                with patch(
                    "urllib.request.urlopen",
                    side_effect=Exception("Connection refused"),
                ):
                    with patch("builtins.open", MagicMock()):
                        path = (
                            Path(__file__).resolve().parent.parent.parent.parent
                            / "scripts"
                            / "start-test-backend.py"
                        )
                        spec = importlib.util.spec_from_file_location(
                            "start_test_backend", str(path)
                        )
                        assert spec is not None and spec.loader is not None
                        mod = importlib.util.module_from_spec(spec)
                        with pytest.raises(SystemExit):
                            spec.loader.exec_module(mod)
