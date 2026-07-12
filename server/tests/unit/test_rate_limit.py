def test_rate_limit_imports():
    from rate_limit import limiter; assert limiter is not None
