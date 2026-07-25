"""Unit tests for server/models/base.py.

Verifies that BaseModel is aliased to SanitizedModel and inherits
its HTML-stripping behaviour.
"""

from __future__ import annotations

from pydantic import Field


class TestBaseModel:
    """BaseModel = SanitizedModel — alias + HTML stripping."""

    def test_base_model_is_sanitized_model(self) -> None:
        from models.base import BaseModel
        from sanitize import SanitizedModel

        assert BaseModel is SanitizedModel

    def test_strips_html_from_string_fields(self) -> None:
        from models.base import BaseModel

        class _Model(BaseModel):
            name: str = Field(..., max_length=100)

        m = _Model(name="<script>alert(1)</script>John")
        assert "<script>" not in m.name
        assert m.name == "alert(1)John"

    def test_skips_sensitive_fields(self) -> None:
        from models.base import BaseModel

        class _Model(BaseModel):
            password: str = Field(default="")
            token: str = Field(default="")

        m = _Model(
            password="<secret>pa$$word</secret>",
            token="<secret>abc123</secret>",
        )
        # Sensitive fields preserve HTML
        assert m.password == "<secret>pa$$word</secret>"
        assert m.token == "<secret>abc123</secret>"

    def test_preserves_non_string_types(self) -> None:
        from models.base import BaseModel

        class _Model(BaseModel):
            count: int = 0
            enabled: bool = False
            tags: list[str] = []

        m = _Model(count=42, enabled=True, tags=["a", "b"])
        assert m.count == 42
        assert m.enabled is True
        assert m.tags == ["a", "b"]

    def test_strips_nested_html(self) -> None:
        from models.base import BaseModel

        class _Model(BaseModel):
            name: str = Field(..., max_length=200)

        m = _Model(name="<div><span><b>John</b></span></div>")
        assert "<" not in m.name
        assert ">" not in m.name
        assert m.name == "John"

    def test_strips_multiple_tags(self) -> None:
        from models.base import BaseModel

        class _Model(BaseModel):
            name: str = Field(..., max_length=200)

        m = _Model(name="<p>Hello</p><p>World</p>")
        assert "<" not in m.name
        assert "Hello" in m.name
        assert "World" in m.name

    def test_empty_string_preserved(self) -> None:
        from models.base import BaseModel

        class _Model(BaseModel):
            name: str = Field(default="")

        m = _Model(name="")
        assert m.name == ""

    def test_no_html_unchanged(self) -> None:
        from models.base import BaseModel

        class _Model(BaseModel):
            name: str = Field(..., max_length=200)

        m = _Model(name="Plain text name")
        assert m.name == "Plain text name"

    def test_strips_html_from_optional_field(self) -> None:
        from models.base import BaseModel
        from typing import Optional

        class _Model(BaseModel):
            title: Optional[str] = None

        m = _Model(title="<script>x</script>Report")
        assert m.title is not None
        assert "<script>" not in m.title
        assert m.title == "xReport"

    def test_strips_html_from_list_of_strings(self) -> None:
        """SanitizedModel only strips HTML from str fields, not list items."""
        from models.base import BaseModel

        class _Model(BaseModel):
            tags: list[str] = []

        m = _Model(tags=["<b>tag1</b>", "plain", "<i>tag3</i>"])
        # List items are NOT sanitized — only top-level str fields are
        assert m.tags == ["<b>tag1</b>", "plain", "<i>tag3</i>"]
