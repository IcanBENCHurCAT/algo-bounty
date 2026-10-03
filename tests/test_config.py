import os
from unittest.mock import patch
from gateway.config import settings

def test_config_properties():
    with patch.dict(os.environ, {
        "SECRET_KEY": "secret",
        "GITHUB_TOKEN": "token",
        "PLATFORM_PRIVATE_KEY": "pkey",
        "GITHUB_WEBHOOK_SECRET": "wsec",
        "WEBHOOK_API_KEY": "apikey",
        "ALGORAND_NETWORK": "mainnet",
        "SUPABASE_URL": "surl",
        "DATABASE_URL": "dburl"
    }):
        assert settings.SECRET_KEY == "secret"
        assert settings.GITHUB_TOKEN == "token"
        assert settings.PLATFORM_PRIVATE_KEY == "pkey"
        assert settings.GITHUB_WEBHOOK_SECRET == "wsec"
        assert settings.WEBHOOK_API_KEY == "apikey"
        assert settings.ALGORAND_NETWORK == "mainnet"
        assert settings.SUPABASE_URL == "surl"
        assert settings.DATABASE_URL == "dburl"

def test_config_whitespace_strip():
    with patch.dict(os.environ, {
        "SECRET_KEY": "  secret_with_spaces  \n",
        "DATABASE_URL": "postgresql://user:pass@host:5432/postgres\r\n"
    }):
        assert settings.SECRET_KEY == "secret_with_spaces"
        assert settings.DATABASE_URL == "postgresql://user:pass@host:5432/postgres"

def test_config_webhook_secrets_required_on_mainnet():
    import pytest
    with patch.dict(os.environ, {
        "ALGORAND_NETWORK": "mainnet",
        "SECRET_KEY": "secret",
        "GITHUB_TOKEN": "token",
        "PLATFORM_PRIVATE_KEY": "pkey"
    }):
        if "GITHUB_WEBHOOK_SECRET" in os.environ:
            del os.environ["GITHUB_WEBHOOK_SECRET"]
        if "WEBHOOK_API_KEY" in os.environ:
            del os.environ["WEBHOOK_API_KEY"]

        with pytest.raises(RuntimeError, match="GITHUB_WEBHOOK_SECRET must be set in testnet/mainnet"):
            _ = settings.GITHUB_WEBHOOK_SECRET

        with pytest.raises(RuntimeError, match="WEBHOOK_API_KEY must be set in testnet/mainnet"):
            _ = settings.WEBHOOK_API_KEY
