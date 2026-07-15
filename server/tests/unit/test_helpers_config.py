def test_config_has_jwt_secret():
    from config import settings

    assert settings.jwt_secret is not None


def test_config_has_jwt_algorithm():
    from config import settings

    assert settings.jwt_algorithm in ("HS256", "HS384", "HS512", "RS256")


def test_helpers_imports():
    from helpers import _safe_id, _safe_customer, _sanitize_sql, _paginated, require_role, _call, _sql

    assert callable(_safe_id)
    assert callable(_safe_customer)
    assert callable(_sanitize_sql)
    assert callable(_paginated)
    assert callable(require_role)
    assert callable(_call)
    assert callable(_sql)
