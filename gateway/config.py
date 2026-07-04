import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """
    Centralized configuration and secret management for the AlgoBounty Gateway.

    Currently fetches from environment variables, but designed to be easily
    extended with a real secret manager (e.g., GCP Secret Manager).
    """

    @staticmethod
    def get_secret(key: str, default: str = None) -> str:
        """
        Fetch a secret by key.
        In production, this could call an external secret manager API.
        """
        # Placeholder for real secret manager integration
        # if ENV == "production":
        #    return secret_manager.get(key)

        val = os.environ.get(key, default)
        if not val and not default:
            logger.warning(f"Secret {key} is not set in environment.")
        return val

    @property
    def SECRET_KEY(self) -> str:
        return self.get_secret("SECRET_KEY")

    @property
    def GITHUB_TOKEN(self) -> str:
        return self.get_secret("GITHUB_TOKEN")

    @property
    def GITHUB_APP_ID(self) -> str:
        return self.get_secret("GITHUB_APP_ID")

    @property
    def GITHUB_CLIENT_ID(self) -> str:
        return self.get_secret("GITHUB_CLIENT_ID")

    @property
    def GITHUB_PRIVATE_KEY(self) -> str:
        return self.get_secret("GITHUB_PRIVATE_KEY")

    @property
    def PLATFORM_PRIVATE_KEY(self) -> str:
        return self.get_secret("PLATFORM_PRIVATE_KEY")

    @property
    def GITHUB_WEBHOOK_SECRET(self) -> str:
        return self.get_secret("GITHUB_WEBHOOK_SECRET")

    @property
    def WEBHOOK_API_KEY(self) -> str:
        return self.get_secret("WEBHOOK_API_KEY")

    @property
    def ALGORAND_NETWORK(self) -> str:
        return self.get_secret("ALGORAND_NETWORK", "testnet")

    @property
    def SUPABASE_URL(self) -> str:
        return self.get_secret("SUPABASE_URL")

    @property
    def DATABASE_URL(self) -> str:
        return self.get_secret("DATABASE_URL")

settings = Config()
