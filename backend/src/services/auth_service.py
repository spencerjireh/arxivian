"""Authentication service for Clerk JWT verification."""

from dataclasses import dataclass
from typing import Optional
import httpx
import jwt
from jwt import PyJWKClient

from src.config import get_settings
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

    def __init__(self):
        self._jwks_client: Optional[PyJWKClient] = None
        self._clerk_domain: Optional[str] = None

    def _get_jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client lazily."""
        if self._jwks_client is None:
            settings = get_settings()
            if not settings.clerk_secret_key:
                raise InvalidTokenError("Clerk authentication not configured")

            # Extract Clerk domain from secret key (sk_test_xxx or sk_live_xxx)
            # The domain is in the format: clerk.xxx.xxx.dev or xxx.clerk.accounts.dev
            # For Clerk, we use their standard JWKS endpoint
            self._clerk_domain = self._extract_clerk_domain(settings.clerk_secret_key)
            jwks_url = self.JWKS_URL_TEMPLATE.format(clerk_domain=self._clerk_domain)

            self._jwks_client = PyJWKClient(jwks_url)

        return self._jwks_client

    def _extract_clerk_domain(self, secret_key: str) -> str:
        """
        Extract Clerk frontend API domain from the secret key.

        Note: The actual JWKS URL is derived from the token's issuer claim
        during verification, so this returns a placeholder.
        """
        # The JWKS URL is derived from the token's issuer claim during verification
        # This placeholder is not used since we extract the domain from the token itself
        _ = secret_key  # Acknowledge the parameter
        return "clerk.com"

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
            jwks_url = self.JWKS_URL_TEMPLATE.format(clerk_domain=clerk_domain)

            # Create JWKS client for this domain
            jwks_client = PyJWKClient(jwks_url)

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
        except jwt.InvalidTokenError as e:
            log.warning("token invalid", error=str(e))
            raise InvalidTokenError(f"Token validation failed: {str(e)}")
        except httpx.HTTPError as e:
            log.error("jwks fetch failed", error=str(e))
            raise InvalidTokenError("Unable to verify token")
        except Exception as e:
            log.error("token verification failed", error=str(e), error_type=type(e).__name__)
            raise InvalidTokenError("Token verification failed")


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get singleton auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
