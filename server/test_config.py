"""
Tests for server/config.py.

Tests Settings pydantic model with default values and env overrides.
"""

from __future__ import annotations

from server.config import Settings


class TestConfig:
    """Test suite for config.py."""

    def test_default_values(self):
        """Settings uses documented defaults."""
        s = Settings(_env_file=None)
        assert s.stdb_host == "localhost"
        assert s.stdb_port == 3001
        assert s.stdb_db == "spacetime-crm"
        assert s.server_port == 8723
        assert s.cors_origin == "http://localhost:5185"
        assert s.jwt_algorithm == "HS256"
        assert s.jwt_expire_hours == 24

    def test_stdb_sql_url_property(self):
        """stdb_sql_url builds correctly."""
        s = Settings(stdb_host="test", stdb_port=9999)
        assert s.stdb_sql_url == "http://test:9999/v1/database/spacetime-crm/sql"

    def test_stdb_call_url_property(self):
        """stdb_call_url builds correctly."""
        s = Settings(stdb_host="test", stdb_port=9999)
        assert s.stdb_call_url == "http://test:9999/v1/database/spacetime-crm/call"

    def test_model_config_env_file(self):
        """Settings has env_file configured."""
        assert "env_file" in Settings.model_config
        assert Settings.model_config["env_file"] == ".env"

    def test_settings_is_singleton(self):
        """settings module var is a Settings instance."""
        from server.config import settings

        assert isinstance(settings, Settings)
