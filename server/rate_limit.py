"""Rate limiting for SpacetimeCRM using slowapi.

Tiered limits:
  Auth endpoints        10/minute  (brute-force protection)
  Health endpoint       unlimited  (monitoring / k8s probes)
  Settings / admin      30/minute
  Everything else      100/minute  (default)
"""

from __future__ import annotations

from slowapi import Limiter as _Limiter
from slowapi.util import get_remote_address

limiter = _Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
)
