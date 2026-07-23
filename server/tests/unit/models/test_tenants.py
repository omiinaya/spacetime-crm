"""Tenant models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestTenantCreate:
    def test_valid(self) -> None:
        from models import TenantCreate

        m = TenantCreate(name="Acme Repair")
        assert m.name == "Acme Repair"
        assert m.slug == ""

    def test_empty_name_raises(self) -> None:
        from models import TenantCreate

        with pytest.raises(ValidationError):
            TenantCreate(name="")


class TestTenantMemberAdd:
    def test_valid(self) -> None:
        from models import TenantMemberAdd

        m = TenantMemberAdd(username="alice")
        assert m.username == "alice"
        assert m.role == "user"

    def test_empty_username_raises(self) -> None:
        from models import TenantMemberAdd

        with pytest.raises(ValidationError):
            TenantMemberAdd(username="")
