"""
Tests for server/main.py.

Tests FastAPI app creation, lifespan, CORS, and route registration.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.main import app


class TestMain:
    """Test suite for main.py."""

    def test_app_is_fastapi_instance(self):
        """The app is a FastAPI instance."""
        assert isinstance(app, FastAPI)

    def test_app_title(self):
        """App has the correct title."""
        assert app.title == "SpacetimeCRM"

    def test_cors_middleware_registered(self):
        """CORS middleware is registered on the app."""
        middleware_classes = [m.cls for m in app.user_middleware]
        assert CORSMiddleware in middleware_classes

    def test_cors_allows_credentials(self):
        """CORS allows credentials."""
        cors = None
        for m in app.user_middleware:
            if m.cls == CORSMiddleware:
                cors = m
                break
        assert cors is not None
        assert cors.kwargs.get("allow_credentials") is True

    def test_cors_allows_all_methods(self):
        """CORS allows all methods."""
        cors = None
        for m in app.user_middleware:
            if m.cls == CORSMiddleware:
                cors = m
                break
        assert cors is not None
        assert cors.kwargs.get("allow_methods") == ["*"]

    def test_cors_allows_all_headers(self):
        """CORS allows all headers."""
        cors = None
        for m in app.user_middleware:
            if m.cls == CORSMiddleware:
                cors = m
                break
        assert cors is not None
        assert cors.kwargs.get("allow_headers") == ["*"]
