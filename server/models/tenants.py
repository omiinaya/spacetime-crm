"""Tenant request models."""

from pydantic import Field

from .base import BaseModel


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(default="", max_length=255)


class TenantUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(default="", max_length=255)
    logo_url: str = Field(default="", max_length=1000)
    settings: str = Field(default="{}", max_length=10000)


class TenantMemberAdd(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="user", max_length=50)


class TenantMemberRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)


class TenantMigrate(BaseModel):
    name: str = Field(default="Default", max_length=255)
    slug: str = Field(default="", max_length=255)
