"""Shared base model — SanitizedModel with HTML stripping."""

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel
