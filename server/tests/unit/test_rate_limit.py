"""Unit tests for server/rate_limit.py.

Tests that the limiter export is correctly configured as a slowapi.Limiter
instance with the expected default limits.
"""

from __future__ import annotations

from slowapi import Limiter


class TestLimiter:
    """Rate limiter singleton configuration."""

    def test_limiter_is_slowapi_limiter(self) -> None:
        from rate_limit import limiter

        assert isinstance(limiter, Limiter)

    def test_limiter_has_default_limits(self) -> None:
        from rate_limit import limiter

        assert hasattr(limiter, "_default_limits")
        assert len(limiter._default_limits) >= 1
        # The limit string should contain "100/minute"
        limit_group = limiter._default_limits[0]
        limit_str = limit_group._LimitGroup__limit_provider
        assert "100/minute" in limit_str

    def test_limiter_key_function_is_remote_address(self) -> None:
        from rate_limit import limiter
        from slowapi.util import get_remote_address

        assert limiter._key_func is get_remote_address

    def test_limiter_singleton(self) -> None:
        from rate_limit import limiter as limiter_first
        from rate_limit import limiter as limiter_second

        assert limiter_first is limiter_second
