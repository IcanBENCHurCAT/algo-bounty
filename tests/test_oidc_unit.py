import pytest
import jwt
from unittest.mock import patch, AsyncMock, MagicMock
from gateway.oidc import get_github_jwks, verify_github_oidc_token, GITHUB_OIDC_ISSUER

@pytest.mark.asyncio
async def test_get_github_jwks():
    mock_config = {"jwks_uri": "https://keys.url"}
    mock_jwks = {"keys": [{"kid": "123"}]}

    with patch("httpx.AsyncClient.get") as mock_get:
        # First call for config, second for jwks
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: mock_config, raise_for_status=lambda: None),
            MagicMock(status_code=200, json=lambda: mock_jwks, raise_for_status=lambda: None)
        ]

        # Clear cache
        import gateway.oidc
        gateway.oidc._jwks_cache = None

        jwks = await get_github_jwks()
        assert jwks == mock_jwks
        assert gateway.oidc._jwks_cache == mock_jwks

@pytest.mark.asyncio
async def test_verify_github_oidc_token_success():
    # We need to mock the RSA key and jwt.decode
    mock_jwks = {"keys": [{"kid": "kid1", "n": "...", "e": "..."}]}
    token = "header.payload.sig"

    with patch("gateway.oidc.get_github_jwks", new_callable=AsyncMock) as mock_get_jwks, \
         patch("jwt.get_unverified_header", return_value={"kid": "kid1"}), \
         patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value="public_key"), \
         patch("jwt.decode", return_value={"repository": "owner/repo", "workflow": "wf1", "aud": "aud1"}):

        mock_get_jwks.return_value = mock_jwks

        payload = await verify_github_oidc_token(token, expected_aud="aud1", expected_repo="owner/repo", expected_workflow="wf1")
        assert payload["repository"] == "owner/repo"

@pytest.mark.asyncio
async def test_verify_github_oidc_token_mismatch():
    mock_jwks = {"keys": [{"kid": "kid1"}]}
    token = "header.payload.sig"

    with patch("gateway.oidc.get_github_jwks", new_callable=AsyncMock) as mock_get_jwks, \
         patch("jwt.get_unverified_header", return_value={"kid": "kid1"}), \
         patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value="public_key"), \
         patch("jwt.decode", return_value={"repository": "wrong/repo"}):

        mock_get_jwks.return_value = mock_jwks

        with pytest.raises(jwt.InvalidTokenError, match="Repository mismatch"):
            await verify_github_oidc_token(token, expected_repo="owner/repo")
