"""Authentication service for Clerk JWT verification."""

from dataclasses import dataclass
from typing import Optional
import jwt
from jwt import PyJWKClient

from src.exceptions import InvalidTokenError, MissingTokenError
from src.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user from Clerk JWT."""

    clerk_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None


class AuthService:
    """Service for verifying Clerk JWTs using JWKS."""

    # Clerk JWKS URL pattern
    JWKS_URL_TEMPLATE = "https://{clerk_domain}/.well-known/jwks.json"

    def __init__(self, allowed_domain: str) -> None:
        self._allowed_domain = allowed_domain
        self._jwks_clients: dict[str, PyJWKClient] = {}

    _MAX_JWKS_CLIENTS = 10

    def _get_jwks_client(self, clerk_domain: str) -> PyJWKClient:
        """Get or create a cached PyJWKClient for the given Clerk domain."""
        if clerk_domain not in self._jwks_clients:
            if len(self._jwks_clients) >= self._MAX_JWKS_CLIENTS:
                self._jwks_clients.clear()
            jwks_url = self.JWKS_URL_TEMPLATE.format(clerk_domain=clerk_domain)
            self._jwks_clients[clerk_domain] = PyJWKClient(jwks_url)
        return self._jwks_clients[clerk_domain]

    async def verify_token(self, authorization_header: Optional[str]) -> AuthenticatedUser:
        """
        Verify Clerk JWT and extract user information.

        Args:
            authorization_header: The Authorization header value (Bearer <token>)

        Returns:
            AuthenticatedUser with user details from the token

        Raises:
            MissingTokenError: If no token is provided
            InvalidTokenError: If token is invalid or expired
        """
        if not authorization_header:
            raise MissingTokenError()

        # Extract token from Bearer scheme
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise InvalidTokenError("Invalid authorization header format")

        token = parts[1]

        try:
            # First, decode without verification to get the issuer
            unverified = jwt.decode(token, options={"verify_signature": False})
            issuer = unverified.get("iss", "")

            # Clerk issuer format: https://<clerk-domain>
            if not issuer or not issuer.startswith("https://"):
                raise InvalidTokenError("Invalid token issuer")

            # Extract domain from issuer for JWKS lookup
            clerk_domain = issuer.replace("https://", "")

            if clerk_domain != self._allowed_domain:
                raise InvalidTokenError("Token issuer not trusted")

            # Get cached JWKS client for this domain
            jwks_client = self._get_jwks_client(clerk_domain)

            # Get the signing key
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Verify and decode the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=issuer,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                },
            )

            # Extract user information from Clerk token claims
            # Clerk stores user ID in 'sub' claim
            clerk_id = payload.get("sub")
            if not clerk_id:
                raise InvalidTokenError("Token missing user identifier")

            # Additional claims that may be present
            email = payload.get("email")
            first_name = payload.get("first_name")
            last_name = payload.get("last_name")
            profile_image_url = payload.get("image_url") or payload.get("profile_image_url")

            log.debug(
                "token verified",
                clerk_id=clerk_id,
                email=email,
            )

            return AuthenticatedUser(
                clerk_id=clerk_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=profile_image_url,
            )

        except jwt.ExpiredSignatureError:
            log.warning("token expired")
            raise InvalidTokenError("Token has expired")
        except InvalidTokenError:
            raise
        except jwt.InvalidTokenError as e:
            log.warning("token invalid", error=str(e))
            raise InvalidTokenError(f"Token validation failed: {str(e)}")
        except Exception as e:
            log.error("token verification failed", error=str(e), error_type=type(e).__name__)
            raise InvalidTokenError("Token verification failed")


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get singleton auth service instance."""
    global _auth_service
    if _auth_service is None:
        from src.config import get_settings

        settings = get_settings()
        _auth_service = AuthService(allowed_domain=settings.clerk_domain)
    return _auth_service
