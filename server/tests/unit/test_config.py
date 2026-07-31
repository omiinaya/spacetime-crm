"""Unit tests for server/config.py.

Tests the Pydantic Settings model, default values, env var overrides,
and computed URL properties.
"""

from __future__ import annotations


class TestSettingsDefaults:
    """Default values of the Settings model."""

    def test_default_host(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_HOST", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        assert s.stdb_host == "localhost"

    def test_default_port(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_PORT", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        assert s.stdb_port == 3001

    def test_default_db(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_DB", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        assert s.stdb_db == "spacetime-crm"

    def test_default_server_port(self, monkeypatch) -> None:
        monkeypatch.delenv("SERVER_PORT", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        assert s.server_port == 8723

    def test_default_cors_origin(self, monkeypatch) -> None:
        monkeypatch.delenv("CORS_ORIGIN", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        assert s.cors_origin == "http://localhost:5185"

    def test_default_jwt_secret(self, monkeypatch) -> None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        assert s.jwt_secret == "change-me-to-a-random-secret"

    def test_default_jwt_algorithm(self) -> None:
        from config import Settings

        s = Settings(_env_file=None)
        assert s.jwt_algorithm == "HS256"

    def test_default_jwt_expire_hours(self) -> None:
        from config import Settings

        s = Settings(_env_file=None)
        assert s.jwt_expire_hours == 24

    def test_default_app_url(self) -> None:
        from config import Settings

        s = Settings(_env_file=None)
        assert s.app_url == "http://localhost:8723"


class TestComputedUrlProperties:
    """Computed URL properties based on host, port, and db."""

    def test_stdb_sql_url_default(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_HOST", raising=False)
        monkeypatch.delenv("STDB_PORT", raising=False)
        monkeypatch.delenv("STDB_DB", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        expected = "http://localhost:3001/v1/database/spacetime-crm/sql"
        assert s.stdb_sql_url == expected

    def test_stdb_call_url_default(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_HOST", raising=False)
        monkeypatch.delenv("STDB_PORT", raising=False)
        monkeypatch.delenv("STDB_DB", raising=False)
        from config import Settings

        s = Settings(_env_file=None)
        expected = "http://localhost:3001/v1/database/spacetime-crm/call"
        assert s.stdb_call_url == expected

    def test_stdb_sql_url_custom_host(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_DB", raising=False)
        from config import Settings

        s = Settings(stdb_host="stdb.example.com", _env_file=None)
        expected = "http://stdb.example.com:3001/v1/database/spacetime-crm/sql"
        assert s.stdb_sql_url == expected

    def test_stdb_call_url_custom_host(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_DB", raising=False)
        from config import Settings

        s = Settings(stdb_host="stdb.example.com", _env_file=None)
        expected = "http://stdb.example.com:3001/v1/database/spacetime-crm/call"
        assert s.stdb_call_url == expected

    def test_stdb_sql_url_custom_port(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_HOST", raising=False)
        monkeypatch.delenv("STDB_DB", raising=False)
        from config import Settings

        s = Settings(stdb_port=8080, _env_file=None)
        expected = "http://localhost:8080/v1/database/spacetime-crm/sql"
        assert s.stdb_sql_url == expected

    def test_stdb_call_url_custom_db(self, monkeypatch) -> None:
        monkeypatch.delenv("STDB_HOST", raising=False)
        monkeypatch.delenv("STDB_PORT", raising=False)
        from config import Settings

        s = Settings(stdb_db="my-app", _env_file=None)
        expected = "http://localhost:3001/v1/database/my-app/call"
        assert s.stdb_call_url == expected

    def test_stdb_urls_with_all_custom(self) -> None:
        from config import Settings

        s = Settings(stdb_host="10.0.0.1", stdb_port=5000, stdb_db="production", _env_file=None)
        assert s.stdb_sql_url == "http://10.0.0.1:5000/v1/database/production/sql"
        assert s.stdb_call_url == "http://10.0.0.1:5000/v1/database/production/call"


class TestEnvVarOverrides:
    """Settings can be overridden via environment variables."""

    def test_env_var_stdb_host(self, monkeypatch) -> None:
        monkeypatch.setenv("STDB_HOST", "env-host.example.com")
        from config import Settings

        s = Settings()
        assert s.stdb_host == "env-host.example.com"

    def test_env_var_stdb_port(self, monkeypatch) -> None:
        monkeypatch.setenv("STDB_PORT", "9999")
        from config import Settings

        s = Settings()
        assert s.stdb_port == 9999

    def test_env_var_stdb_db(self, monkeypatch) -> None:
        monkeypatch.setenv("STDB_DB", "env-db")
        from config import Settings

        s = Settings()
        assert s.stdb_db == "env-db"

    def test_env_var_server_port(self, monkeypatch) -> None:
        monkeypatch.setenv("SERVER_PORT", "8080")
        from config import Settings

        s = Settings()
        assert s.server_port == 8080

    def test_env_var_multiple_computed(self, monkeypatch) -> None:
        monkeypatch.setenv("STDB_HOST", "staging.local")
        monkeypatch.setenv("STDB_PORT", "4000")
        monkeypatch.setenv("STDB_DB", "staging-crm")
        from config import Settings

        s = Settings()
        assert s.stdb_sql_url == "http://staging.local:4000/v1/database/staging-crm/sql"
        assert s.stdb_call_url == "http://staging.local:4000/v1/database/staging-crm/call"
