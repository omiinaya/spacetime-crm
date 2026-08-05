"""Shared httpx.AsyncClient with connection pooling.

Minimal module with zero internal dependencies — safe to import from anywhere
without creating circular imports.

The shared client is loop-aware: httpx.AsyncClient binds its connection pool
to the event loop that was running at first request. Under pytest, tests mix
transient loops (``asyncio.run()`` in unit tests) with pytest-asyncio loops, so
a single loop-agnostic singleton would keep pooled transports pointing at a
closed loop and raise ``RuntimeError: Event loop is closed`` on later use.
``get_http_client()`` therefore recreates the client whenever the current loop
differs from the loop it was created on. In production (one long-lived uvicorn
loop) the singleton is still created exactly once.
"""

from __future__ import annotations

import asyncio

import httpx
from httpx import Limits, Timeout

_shared_client: httpx.AsyncClient | None = None
_shared_client_loop: asyncio.AbstractEventLoop | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return a shared AsyncClient with connection pooling.

    Reuse this across the app instead of creating inline ``httpx.AsyncClient()``
    instances.  Per-call timeouts are honoured via the ``timeout`` kwarg on each
    request method.

    The client is (re)created per event loop: see the module docstring for why.
    """
    global _shared_client, _shared_client_loop

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Called from a synchronous context (no running loop). Python 3.11's
        # asyncio.get_event_loop() raises here when no loop is current, so use
        # None as the marker: consecutive sync calls share the client, and any
        # async caller (loop is not None) gets its own loop-bound client.
        loop = None

    if _shared_client is None or _shared_client_loop is not loop:
        # Discard any client bound to a different (possibly already closed)
        # loop. Dropping the reference lets GC close its pooled sockets; the
        # connection pool must not survive across loop boundaries.
        _shared_client = httpx.AsyncClient(
            timeout=Timeout(30.0),
            limits=Limits(max_keepalive_connections=20, max_connections=100),
        )
        _shared_client_loop = loop
    return _shared_client
