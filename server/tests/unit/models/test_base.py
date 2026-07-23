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
