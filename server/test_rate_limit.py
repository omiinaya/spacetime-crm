"""
Tests for server/rate_limit.py.

Tests slowapi Limiter configuration.
"""

from __future__ import annotations

from slowapi import Limiter

from server.rate_limit import limiter


class TestRateLimit:
    """Test suite for rate_limit.py."""

    def test_limiter_is_instance(self):
        """limiter is a slowapi Limiter instance."""
        assert isinstance(limiter, Limiter)

    def test_limiter_has_default_limits(self):
        """limiter has default_limits configured."""
        assert limiter._default_limits is not None
        assert len(limiter._default_limits) > 0

    def test_limiter_key_func_is_set(self):
        """limiter has a key function for identifying clients."""
        assert limiter._key_func is not None

    def test_limiter_is_enabled(self):
        """limiter is enabled by default."""
        assert limiter.enabled is True
