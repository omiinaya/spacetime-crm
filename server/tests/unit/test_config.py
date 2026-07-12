"""Unit tests for config module."""

import os
from unittest.mock import patch


class TestSettings:
    def test_default_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            assert s.stdb_host == "localhost"
            assert s.stdb_port == 3001
            assert s.stdb_db == "spacetime-crm"
            assert s.server_port == 8723
            assert s.cors_origin == "http://localhost:5185"
            assert s.jwt_secret == "set-via-environment-variable"

    def test_stdb_urls_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            expected_sql = "http://localhost:3001/v1/database/spacetime-crm/sql"
            expected_call = "http://localhost:3001/v1/database/spacetime-crm/call"
            assert s.stdb_sql_url == expected_sql
            assert s.stdb_call_url == expected_call

    def test_stdb_urls_custom(self) -> None:
        env = {"STDB_HOST": "stdb.example.com", "STDB_PORT": "5432", "STDB_DB": "testdb"}
        with patch.dict(os.environ, env, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            expected = "http://stdb.example.com:5432/v1/database/testdb/sql"
            assert s.stdb_sql_url == expected

    def test_jwt_secret_env(self) -> None:
        env = {"JWT_SECRET": "my-test-secret"}
        with patch.dict(os.environ, env, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            assert s.jwt_secret == "my-test-secret"

    def test_server_port_env(self) -> None:
        with patch.dict(os.environ, {"SERVER_PORT": "9999"}, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            assert s.server_port == 9999

    def test_cors_origin_env(self) -> None:
        with patch.dict(os.environ, {"CORS_ORIGIN": "http://example.com"}, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            assert s.cors_origin == "http://example.com"

    def test_stripe_secret_env(self) -> None:
        env = {"STRIPE_SECRET_KEY": "sk_test_123", "STRIPE_WEBHOOK_SECRET": "whsec_456"}
        with patch.dict(os.environ, env, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            assert s.stripe_secret_key == "sk_test_123"
            assert s.stripe_webhook_secret == "whsec_456"

    def test_app_url_env(self) -> None:
        with patch.dict(os.environ, {"APP_URL": "https://myapp.example.com"}, clear=True):
            from config import Settings

            s = Settings(_env_file=None)
            assert s.app_url == "https://myapp.example.com"
