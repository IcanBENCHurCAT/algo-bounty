import httpx
import jwt
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

GITHUB_OIDC_DISCOVERY_URL = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"

# Cache for JWKS to avoid fetching it every time
_jwks_cache: Optional[Dict[str, Any]] = None

async def get_github_jwks() -> Dict[str, Any]:
    """Fetch GitHub's OIDC public keys from the official discovery endpoint."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    try:
        async with httpx.AsyncClient() as client:
            # 1. Fetch OpenID configuration
            config_resp = await client.get(GITHUB_OIDC_DISCOVERY_URL)
            config_resp.raise_for_status()
            config = config_resp.json()
            jwks_uri = config.get("jwks_uri")

            if not jwks_uri:
                raise ValueError("Missing jwks_uri in OpenID configuration")

            # 2. Fetch JWKS
            jwks_resp = await client.get(jwks_uri)
            jwks_resp.raise_for_status()
            _jwks_cache = jwks_resp.json()
            return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch GitHub JWKS: {e}")
        raise

async def verify_github_oidc_token(
    token: str,
    expected_aud: str = "https://github.com/AlgoBounty",
    expected_repo: Optional[str] = None,
    expected_workflow: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify a GitHub Actions OIDC token.

    Args:
        token: The JWT token from GitHub Actions
        expected_aud: Expected audience (defaults to the AlgoBounty platform URL)
        expected_repo: Expected repository (e.g. "owner/repo")
        expected_workflow: Expected workflow name or path

    Returns:
        The decoded payload if valid

    Raises:
        jwt.InvalidTokenError: If validation fails
    """
    jwks = await get_github_jwks()

    # Get the key ID from the header
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    # Find the matching key in JWKS
    key_data = next((key for key in jwks["keys"] if key["kid"] == kid), None)
    if not key_data:
        raise jwt.InvalidTokenError(f"Public key with kid {kid} not found")

    # Construct the public key
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    # Decode and verify
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=expected_aud,
        issuer=GITHUB_OIDC_ISSUER
    )

    # Additional claims verification
    if expected_repo and payload.get("repository") != expected_repo:
        raise jwt.InvalidTokenError(f"Repository mismatch: expected {expected_repo}, got {payload.get('repository')}")

    if expected_workflow and payload.get("workflow") != expected_workflow:
        raise jwt.InvalidTokenError(f"Workflow mismatch: expected {expected_workflow}, got {payload.get('workflow')}")

    return payload
