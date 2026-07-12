"""Unit tests for server/sanitize.py - HTML sanitization.
No server dependencies - pure function tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

import pytest
from typing import Optional
from pydantic import Field


class TestStripHtml:
    def test_removes_simple_tags(self):
        from sanitize import strip_html

        assert strip_html("<b>hello</b>") == "hello"

    def test_removes_script_tags(self):
        from sanitize import strip_html

        result = strip_html('<script>alert("xss")</script>hello')
        assert "script" not in result
        assert result == 'alert("xss")hello'

    def test_preserves_non_html_text(self):
        from sanitize import strip_html

        assert strip_html("Hello, World!") == "Hello, World!"

    def test_handles_nested_tags(self):
        from sanitize import strip_html

        assert strip_html("<div><p>text</p></div>") == "text"

    def test_handles_attributes(self):
        from sanitize import strip_html

        result = strip_html('<a href="http://evil.com">click</a>')
        assert result == "click"

    def test_returns_non_string_as_is(self):
        from sanitize import strip_html

        assert strip_html(42) == 42
        assert strip_html(None) is None
        assert strip_html(3.14) == 3.14

    def test_handles_empty_string(self):
        from sanitize import strip_html

        assert strip_html("") == ""

    def test_handles_malformed_html(self):
        from sanitize import strip_html

        assert strip_html("<b>broken") == "broken"
        assert strip_html("some <text") == "some <text"


class TestSanitizedModel:
    def test_strips_html_from_name(self):
        from sanitize import SanitizedModel

        class TestModel(SanitizedModel):
            name: str = Field(..., max_length=100)
            bio: str = Field(default="", max_length=500)

        obj = TestModel(name="<b>John</b>", bio="<script>alert('x')</script>bio")
        assert obj.name == "John"
        assert obj.bio == "alert('x')bio"

    def test_preserves_password_field(self):
        from sanitize import SanitizedModel

        class TestModel(SanitizedModel):
            password: str = Field(default="", max_length=100)

        obj = TestModel(password="<b>secret</b>")
        assert obj.password == "<b>secret</b>"

    def test_preserves_token_field(self):
        from sanitize import SanitizedModel

        class TestModel(SanitizedModel):
            token: str = Field(default="", max_length=100)

        obj = TestModel(token="<b>tok</b>")
        assert obj.token == "<b>tok</b>"

    def test_default_values_unchanged(self):
        from sanitize import SanitizedModel

        class TestModel(SanitizedModel):
            name: str = Field(..., max_length=100)
            bio: str = Field(default="default bio", max_length=500)
            password: str = Field(default="", max_length=100)

        obj = TestModel(name="Safe Name")
        assert obj.name == "Safe Name"
        assert obj.bio == "default bio"
        assert obj.password == ""

    def test_multiple_string_fields(self):
        from sanitize import SanitizedModel

        class TestModel(SanitizedModel):
            first_name: str = Field(..., max_length=100)
            last_name: str = Field(..., max_length=100)
            notes: str = Field(default="", max_length=500)

        obj = TestModel(
            first_name="<i>Jane</i>",
            last_name="<b>Doe</b>",
            notes="<a href='x'>link</a>",
        )
        assert obj.first_name == "Jane"
        assert obj.last_name == "Doe"
        assert obj.notes == "link"

    def test_skip_sanitize_includes_common_secrets(self):
        from sanitize import _SKIP_SANITIZE

        assert "password" in _SKIP_SANITIZE
        assert "token" in _SKIP_SANITIZE
        assert "secret" in _SKIP_SANITIZE
        assert "smtp_password" in _SKIP_SANITIZE
        assert "twilio_auth_token" in _SKIP_SANITIZE
