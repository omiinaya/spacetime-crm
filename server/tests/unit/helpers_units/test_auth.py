"""Unit tests for helpers.require_role and get_current_user auth dependencies."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException


# ===================================================================
# require_role  — FastAPI auth dependency factory
# ===================================================================


class TestRequireRole:
    """require_role dependency factory — JWT validation + role check."""

    @pytest.mark.asyncio
    async def test_no_credentials_returns_401(self) -> None:
        """When credentials is None, raise 401."""
        from helpers import require_role

        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc:
            await checker(None)
        assert exc.value.status_code == 401
        assert "Not authenticated" in exc.value.detail

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self) -> None:
        """Expired JWT should raise 401."""
        mock_creds = MagicMock()
        mock_creds.credentials = "expired.jwt.token"

        with patch("helpers.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("expired")
            from helpers import require_role

            checker = require_role("admin")
            with pytest.raises(HTTPException) as exc:
                await checker(mock_creds)
            assert exc.value.status_code == 401
            assert "Token expired" in exc.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self) -> None:
        """Garbled JWT should raise 401."""
        mock_creds = MagicMock()
        mock_creds.credentials = "bad.token"

        with patch("helpers.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError("bad")
            from helpers import require_role

            checker = require_role("admin")
            with pytest.raises(HTTPException) as exc:
                await checker(mock_creds)
            assert exc.value.status_code == 401
            assert "Invalid token" in exc.value.detail

    @pytest.mark.asyncio
    async def test_no_subject_returns_401(self) -> None:
        """Token without subject should raise 401."""
        mock_creds = MagicMock()
        mock_creds.credentials = "valid.jwt.token"

        with patch("helpers.jwt.decode") as mock_decode:
            mock_decode.return_value = {}  # no 'sub'
            from helpers import require_role

            checker = require_role("admin")
            with pytest.raises(HTTPException) as exc:
                await checker(mock_creds)
            assert exc.value.status_code == 401
            assert "no subject" in exc.value.detail

    @pytest.mark.asyncio
    async def test_user_not_found_returns_401(self) -> None:
        """JWT valid but user not in DB -> 401."""
        mock_creds = MagicMock()
        mock_creds.credentials = "valid.jwt.token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-1", "tenant_id": "t-1"}
            mock_sql.return_value = []  # no user found
            from helpers import require_role

            checker = require_role("admin")
            with pytest.raises(HTTPException) as exc:
                await checker(mock_creds)
            assert exc.value.status_code == 401
            assert "User not found" in exc.value.detail

    @pytest.mark.asyncio
    async def test_disabled_user_returns_403(self) -> None:
        """Inactive user should raise 403."""
        mock_creds = MagicMock()
        mock_creds.credentials = "valid.jwt.token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-1", "tenant_id": "t-1"}
            mock_sql.return_value = [{"id": "u-1", "active": False, "role": "admin"}]
            from helpers import require_role

            checker = require_role("admin")
            with pytest.raises(HTTPException) as exc:
                await checker(mock_creds)
            assert exc.value.status_code == 403
            assert "disabled" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_wrong_role_returns_403(self) -> None:
        """User with wrong role should raise 403."""
        mock_creds = MagicMock()
        mock_creds.credentials = "valid.jwt.token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-1", "tenant_id": "t-1"}
            mock_sql.return_value = [
                {
                    "id": "u-1",
                    "active": True,
                    "role": "staff",
                }
            ]
            from helpers import require_role

            checker = require_role("admin", "superadmin")
            with pytest.raises(HTTPException) as exc:
                await checker(mock_creds)
            assert exc.value.status_code == 403
            assert "Access denied" in exc.value.detail
            assert "admin" in exc.value.detail
            assert "staff" in exc.value.detail

    @pytest.mark.asyncio
    async def test_successful_auth(self) -> None:
        """Valid token + matching role should return user dict."""
        mock_creds = MagicMock()
        mock_creds.credentials = "valid.jwt.token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-1", "tenant_id": "t-1"}
            mock_sql.return_value = [
                {
                    "id": "u-1",
                    "role": "admin",
                    "active": True,
                    "name": "Alice",
                }
            ]
            from helpers import require_role

            checker = require_role("admin")
            user = await checker(mock_creds)

        assert user["id"] == "u-1"
        assert user["role"] == "admin"
        assert user["tenant_id"] == "t-1"

    @pytest.mark.asyncio
    async def test_jwt_decode_called_with_secret(self) -> None:
        """Should pass settings.jwt_secret and algorithm to jwt.decode."""
        mock_creds = MagicMock()
        mock_creds.credentials = "some.jwt.token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-1", "tenant_id": "t-1"}
            mock_sql.return_value = [
                {
                    "id": "u-1",
                    "role": "admin",
                    "active": True,
                }
            ]
            from helpers import require_role, settings

            checker = require_role("admin")
            await checker(mock_creds)

        mock_decode.assert_called_once_with(
            "some.jwt.token",
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )


# ===================================================================
# get_current_user  — JWT auth dependency
# ===================================================================


class TestGetCurrentUser:
    """Standalone JWT auth dependency (same logic as require_role)."""

    @pytest.mark.asyncio
    async def test_no_credentials_401(self) -> None:
        from helpers import get_current_user

        with pytest.raises(HTTPException) as exc:
            await get_current_user(None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_successful_auth_returns_user(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "valid.token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-42", "tenant_id": "t-7"}
            mock_sql.return_value = [
                {
                    "id": "u-42",
                    "role": "admin",
                    "active": True,
                    "name": "Bob",
                }
            ]
            from helpers import get_current_user

            user = await get_current_user(mock_creds)

        assert user["id"] == "u-42"
        assert user["tenant_id"] == "t-7"
        assert user["role"] == "admin"

    @pytest.mark.asyncio
    async def test_disabled_user_403(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "valid.token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-1", "tenant_id": "t-1"}
            mock_sql.return_value = [
                {
                    "id": "u-1",
                    "role": "admin",
                    "active": False,
                }
            ]
            from helpers import get_current_user

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_creds)
            assert exc.value.status_code == 403
            assert "disabled" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_expired_token(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "expired.token"

        with patch("helpers.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError()
            from helpers import get_current_user

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_creds)
            assert exc.value.status_code == 401
            assert "Token expired" in exc.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "bad.token"

        with patch("helpers.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError()
            from helpers import get_current_user

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_creds)
            assert exc.value.status_code == 401
            assert "Invalid token" in exc.value.detail

    @pytest.mark.asyncio
    async def test_no_subject(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "token"

        with patch("helpers.jwt.decode") as mock_decode:
            mock_decode.return_value = {}
            from helpers import get_current_user

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_creds)
            assert exc.value.status_code == 401
            assert "no subject" in exc.value.detail

    @pytest.mark.asyncio
    async def test_user_not_found(self) -> None:
        mock_creds = MagicMock()
        mock_creds.credentials = "token"

        with (
            patch("helpers.jwt.decode") as mock_decode,
            patch("helpers._sql", new_callable=AsyncMock) as mock_sql,
        ):
            mock_decode.return_value = {"sub": "u-99"}
            mock_sql.return_value = []
            from helpers import get_current_user

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_creds)
            assert exc.value.status_code == 401
            assert "User not found" in exc.value.detail
