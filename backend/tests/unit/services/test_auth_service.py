"""Unit tests for AuthService JWT verification."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import jwt as pyjwt

from src.services.auth_service import AuthService, AuthenticatedUser
from src.exceptions import InvalidTokenError, MissingTokenError


class TestAuthServiceVerifyToken:
    """Tests for AuthService.verify_token method."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance for testing."""
        return AuthService()

    @pytest.mark.asyncio
    async def test_verify_token_missing_header_raises_error(self, auth_service):
        """Verify MissingTokenError when no Authorization header."""
        with pytest.raises(MissingTokenError):
            await auth_service.verify_token(None)

    @pytest.mark.asyncio
    async def test_verify_token_empty_header_raises_error(self, auth_service):
        """Verify MissingTokenError when empty Authorization header."""
        with pytest.raises(MissingTokenError):
            await auth_service.verify_token("")

    @pytest.mark.asyncio
    async def test_verify_token_invalid_scheme_raises_error(self, auth_service):
        """Verify InvalidTokenError for non-Bearer scheme."""
        with pytest.raises(InvalidTokenError) as exc_info:
            await auth_service.verify_token("Basic abc123")

        assert "Invalid authorization header format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_token_missing_token_part_raises_error(self, auth_service):
        """Verify InvalidTokenError when Bearer has no token."""
        with pytest.raises(InvalidTokenError) as exc_info:
            await auth_service.verify_token("Bearer")

        assert "Invalid authorization header format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_token_malformed_jwt_raises_error(self, auth_service):
        """Verify InvalidTokenError for unparseable token."""
        with pytest.raises(InvalidTokenError):
            await auth_service.verify_token("Bearer not.a.valid.jwt")

    @pytest.mark.asyncio
    async def test_verify_token_invalid_issuer_raises_error(
        self, auth_service, valid_jwt_payload
    ):
        """Verify InvalidTokenError when issuer doesn't start with https://."""
        # Create payload with invalid issuer (not https://)
        invalid_payload = {**valid_jwt_payload, "iss": "http://insecure.example.com"}

        with patch.object(pyjwt, "decode") as mock_decode:
            mock_decode.return_value = invalid_payload

            with pytest.raises(InvalidTokenError):
                await auth_service.verify_token("Bearer some.valid.looking.token")

    @pytest.mark.asyncio
    async def test_verify_token_missing_issuer_raises_error(
        self, auth_service, valid_jwt_payload
    ):
        """Verify InvalidTokenError when issuer is missing."""
        invalid_payload = {k: v for k, v in valid_jwt_payload.items() if k != "iss"}

        with patch.object(pyjwt, "decode") as mock_decode:
            mock_decode.return_value = invalid_payload

            with pytest.raises(InvalidTokenError):
                await auth_service.verify_token("Bearer some.token")

    @pytest.mark.asyncio
    async def test_verify_token_expired_raises_error(self, auth_service):
        """Verify InvalidTokenError for expired tokens."""
        with patch.object(pyjwt, "decode") as mock_decode:
            mock_decode.side_effect = pyjwt.ExpiredSignatureError("Token expired")

            with pytest.raises(InvalidTokenError) as exc_info:
                await auth_service.verify_token("Bearer expired.token")

            assert "Token has expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_token_missing_sub_raises_error(
        self, auth_service, valid_jwt_payload
    ):
        """Verify InvalidTokenError when sub claim is missing."""
        # Payload without sub claim
        payload_without_sub = {k: v for k, v in valid_jwt_payload.items() if k != "sub"}

        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock-key"

        with patch.object(pyjwt, "decode") as mock_decode, \
             patch("src.services.auth_service.PyJWKClient") as mock_jwks_class:

            # First call is unverified decode (needs issuer), second is verified (no sub)
            mock_decode.side_effect = [valid_jwt_payload, payload_without_sub]

            mock_jwks_instance = MagicMock()
            mock_jwks_instance.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks_class.return_value = mock_jwks_instance

            # The specific error gets wrapped in a generic message by the exception handler
            with pytest.raises(InvalidTokenError):
                await auth_service.verify_token("Bearer valid.looking.token")

    @pytest.mark.asyncio
    async def test_verify_token_success_returns_user(
        self, auth_service, valid_jwt_payload
    ):
        """Verify returns AuthenticatedUser with correct fields."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock-key"

        with patch.object(pyjwt, "decode") as mock_decode, \
             patch("src.services.auth_service.PyJWKClient") as mock_jwks_class:

            # First call is unverified decode, second is verified
            mock_decode.side_effect = [valid_jwt_payload, valid_jwt_payload]

            mock_jwks_instance = MagicMock()
            mock_jwks_instance.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks_class.return_value = mock_jwks_instance

            result = await auth_service.verify_token("Bearer valid.token")

            assert isinstance(result, AuthenticatedUser)
            assert result.clerk_id == "user_2abc123def456"
            assert result.email == "test@example.com"
            assert result.first_name == "Test"
            assert result.last_name == "User"
            assert result.profile_image_url == "https://example.com/avatar.png"

    @pytest.mark.asyncio
    async def test_verify_token_handles_optional_claims(self, auth_service):
        """Verify works when email/name claims are missing."""
        minimal_payload = {
            "sub": "user_minimal123",
            "iss": "https://test-clerk.clerk.accounts.dev",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
        }

        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock-key"

        with patch.object(pyjwt, "decode") as mock_decode, \
             patch("src.services.auth_service.PyJWKClient") as mock_jwks_class:

            mock_decode.side_effect = [minimal_payload, minimal_payload]

            mock_jwks_instance = MagicMock()
            mock_jwks_instance.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks_class.return_value = mock_jwks_instance

            result = await auth_service.verify_token("Bearer minimal.token")

            assert isinstance(result, AuthenticatedUser)
            assert result.clerk_id == "user_minimal123"
            assert result.email is None
            assert result.first_name is None
            assert result.last_name is None
            assert result.profile_image_url is None

    @pytest.mark.asyncio
    async def test_verify_token_handles_profile_image_url_variants(self, auth_service):
        """Verify handles both image_url and profile_image_url claims."""
        payload_with_image_url = {
            "sub": "user_123",
            "iss": "https://test-clerk.clerk.accounts.dev",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
            "image_url": "https://example.com/image.png",
        }

        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock-key"

        with patch.object(pyjwt, "decode") as mock_decode, \
             patch("src.services.auth_service.PyJWKClient") as mock_jwks_class:

            mock_decode.side_effect = [payload_with_image_url, payload_with_image_url]

            mock_jwks_instance = MagicMock()
            mock_jwks_instance.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks_class.return_value = mock_jwks_instance

            result = await auth_service.verify_token("Bearer token")

            assert result.profile_image_url == "https://example.com/image.png"


class TestAuthServiceJWKSClient:
    """Tests for AuthService JWKS client handling."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance for testing."""
        return AuthService()

    @pytest.mark.asyncio
    async def test_verify_token_jwks_http_error_raises_invalid_token(self, auth_service):
        """Verify InvalidTokenError on JWKS HTTP errors."""
        import httpx

        valid_payload = {
            "sub": "user_123",
            "iss": "https://test-clerk.clerk.accounts.dev",
        }

        with patch.object(pyjwt, "decode") as mock_decode, \
             patch("src.services.auth_service.PyJWKClient") as mock_jwks_class:

            mock_decode.return_value = valid_payload

            mock_jwks_instance = MagicMock()
            mock_jwks_instance.get_signing_key_from_jwt.side_effect = httpx.HTTPError(
                "JWKS endpoint unavailable"
            )
            mock_jwks_class.return_value = mock_jwks_instance

            with pytest.raises(InvalidTokenError) as exc_info:
                await auth_service.verify_token("Bearer valid.token")

            assert "Unable to verify token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_token_jwt_invalid_error_raises_invalid_token(
        self, auth_service
    ):
        """Verify InvalidTokenError on generic JWT errors."""
        valid_payload = {
            "sub": "user_123",
            "iss": "https://test-clerk.clerk.accounts.dev",
        }

        with patch.object(pyjwt, "decode") as mock_decode, \
             patch("src.services.auth_service.PyJWKClient") as mock_jwks_class:

            # First call returns valid payload, second raises error
            mock_decode.side_effect = [
                valid_payload,
                pyjwt.InvalidTokenError("Invalid signature"),
            ]

            mock_jwks_instance = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = "mock-key"
            mock_jwks_instance.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks_class.return_value = mock_jwks_instance

            with pytest.raises(InvalidTokenError) as exc_info:
                await auth_service.verify_token("Bearer invalid.token")

            assert "Token validation failed" in str(exc_info.value)
