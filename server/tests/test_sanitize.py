"""Tests for input sanitization (XSS protection).

Covers the allowlist-based strip_html (bleach) that replaced the old fragile
regex. The regex only matched well-formed, CLOSED tags so payloads like
'<svg onload=alert(1)>' could survive; bleach parses and drops everything
not on the allowlist (none here), and escapes unclosed tags to inert text.
"""
import pytest
from sanitize import strip_html, SanitizedModel, _SKIP_SANITIZE
from pydantic import Field


class _TestModel(SanitizedModel):
    name: str = Field(..., max_length=100)
    bio: str = Field(default="", max_length=500)
    password: str = Field(default="", max_length=100)  # skipped


# ---- The bypass that this fix closes ----
class TestXssBypassFix:
    def test_unclosed_svg_onload_is_neutralized(self):
        # The exact payload from the security card.
        payload = "<svg onload=alert(1)"
        result = strip_html(payload)
        # No raw tag survives -> the payload is inert (escaped text, not markup).
        assert "<svg" not in result
        assert "<" not in result  # fully escaped, no tag opener
        # bleach escapes the bare '<' of an unclosed tag to '&lt;'
        assert result == "&lt;svg onload=alert(1)"

    def test_closed_svg_tag_is_dropped(self):
        assert "<svg onload=alert(1)>" not in strip_html("<svg onload=alert(1)>")
        assert strip_html("<svg onload=alert(1)>") == ""

    def test_img_onerror_is_dropped(self):
        result = strip_html("<img src=x onerror=alert(1)>")
        assert "<img" not in result
        assert "onerror" not in result

    def test_javascript_protocol_in_href_is_removed(self):
        result = strip_html("<a href='javascript:alert(1)'>x</a>")
        assert "javascript:" not in result
        assert "<a " not in result


class TestStripHtml:
    def test_removes_simple_tags(self):
        assert strip_html("<b>hello</b>") == "hello"

    def test_removes_script_tags(self):
        result = strip_html("<script>alert(\"xss\")</script>hello")
        assert "script" not in result
        assert result == "alert(\"xss\")hello"

    def test_preserves_non_html_text(self):
        assert strip_html("Hello, World!") == "Hello, World!"

    def test_handles_nested_tags(self):
        # bleach strips tags but preserves the text (incl. inter-tag whitespace)
        result = strip_html("<div><p>text</p></div>")
        assert "text" in result
        assert "<" not in result

    def test_handles_attributes(self):
        result = strip_html("<a href=\"http://evil.com\">click</a>")
        assert result == "click"

    def test_returns_non_string_as_is(self):
        assert strip_html(123) == 123
        assert strip_html(None) is None

    def test_handles_empty_string(self):
        assert strip_html("") == ""

    def test_handles_malformed_html(self):
        # bleach escapes the bare '<' of an unclosed tag rather than leaving
        # '<b' behind (the old regex left the '<b' prefix intact — unsafe).
        result = strip_html("<b>unclosed")
        assert "<b" not in result


class TestSanitizedModel:
    def test_strips_html_from_name(self):
        m = _TestModel(name="<script>alert(1)</script>John", bio="Hello")
        assert "<script>" not in m.name
        assert m.name == "alert(1)John"

    def test_preserves_password_field(self):
        m = _TestModel(name="John", password="pass<word>")
        assert m.password == "pass<word>"

    def test_default_values_unchanged(self):
        m = _TestModel(name="John")
        assert m.bio == ""

    def test_multiple_string_fields(self):
        m = _TestModel(name="<b>John</b>", bio="Hello <i>World</i>")
        assert m.name == "John"
        assert m.bio == "Hello World"

    def test_skip_sanitize_includes_common_secrets(self):
        assert "password" in _SKIP_SANITIZE
        assert "token" in _SKIP_SANITIZE
        assert "secret" in _SKIP_SANITIZE
        assert "smtp_password" in _SKIP_SANITIZE
        assert "twilio_auth_token" in _SKIP_SANITIZE

    def test_unclosed_payload_neutralized_on_model(self):
        # Regression for the card: an unclosed tag must not survive modeling.
        m = _TestModel(name="<svg onload=alert(1)")
        assert "<svg" not in m.name
