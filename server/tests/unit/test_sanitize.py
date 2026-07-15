import pytest


def test_strip_html():
    from sanitize import strip_html

    r = strip_html("<script>alert(1)</script><p>Hello</p>")
    assert "<script>" not in r
    assert "Hello" in r


def test_sanitized_model():
    from sanitize import SanitizedModel
    from pydantic import Field

    class M(SanitizedModel):
        name: str = Field(default="")

    m = M(name="<script>x</script>Hello")
    assert "<script>" not in m.name
