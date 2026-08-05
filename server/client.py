"""Shared httpx.AsyncClient with connection pooling.

Minimal module with zero internal dependencies — safe to import from anywhere
without creating circular imports.
"""

from __future__ import annotations

import httpx
from httpx import Limits, Timeout

_shared_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return a shared AsyncClient with connection pooling.

    Reuse this across the app instead of creating inline ``httpx.AsyncClient()``
    instances.  Per-call timeouts are honoured via the ``timeout`` kwarg on each
    request method.
    """
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(
            timeout=Timeout(30.0),
            limits=Limits(max_keepalive_connections=20, max_connections=100),
        )
    return _shared_client
