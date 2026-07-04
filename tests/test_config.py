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
