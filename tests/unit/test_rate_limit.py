"""Tests for rate_limit module (slowapi Limiter instantiation)."""

from rate_limit import limiter


class TestLimiterConfig:
    def test_limiter_is_created(self):
        assert limiter is not None

    def test_limiter_has_default_limits(self):
        assert len(limiter._default_limits) > 0

    def test_limiter_default_limit_is_100_per_minute(self):
        limit_strs = []
        for lg in limiter._default_limits:
            for limit in lg:
                limit_strs.append(str(limit.limit))
        assert any("100" in s and "minute" in s for s in limit_strs), \
            f"Expected 100/minute in limits, got: {limit_strs}"

    def test_limiter_has_key_func(self):
        assert limiter._key_func is not None
