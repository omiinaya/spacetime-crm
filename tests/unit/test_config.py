"""Tests for config module (pydantic Settings with computed URLs)."""

from config import Settings


class TestSettingsDefaults:
    def test_default_host(self):
        s = Settings()
        assert s.stdb_host == "localhost"

    def test_default_port(self):
        s = Settings()
        assert s.stdb_port == 3001

    def test_default_db(self):
        s = Settings()
        assert s.stdb_db == "spacetime-crm"

    def test_default_server_port(self):
        s = Settings()
        assert s.server_port == 8723

    def test_default_jwt_algorithm(self):
        s = Settings()
        assert s.jwt_algorithm == "HS256"

    def test_default_cors_origin(self):
        s = Settings()
        assert s.cors_origin == "http://localhost:5185"

    def test_default_jwt_secret(self):
        s = Settings()
        # JWT secret is auto-generated if not set
        assert len(s.jwt_secret) >= 32


class TestSettingsComputedUrls:
    def test_stdb_sql_url_default(self):
        s = Settings()
        assert s.stdb_sql_url == "http://localhost:3001/v1/database/spacetime-crm/sql"

    def test_stdb_call_url_default(self):
        s = Settings()
        assert s.stdb_call_url == "http://localhost:3001/v1/database/spacetime-crm/call"

    def test_stdb_sql_url_custom_host(self):
        s = Settings(stdb_host="192.168.1.100", stdb_port=3002, stdb_db="test-crm")
        assert s.stdb_sql_url == "http://192.168.1.100:3002/v1/database/test-crm/sql"

    def test_stdb_call_url_custom_host(self):
        s = Settings(stdb_host="192.168.1.100", stdb_port=3002, stdb_db="test-crm")
        assert s.stdb_call_url == "http://192.168.1.100:3002/v1/database/test-crm/call"

    def test_app_url_default(self):
        s = Settings()
        assert s.app_url == "http://localhost:8723"
