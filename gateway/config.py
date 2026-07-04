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
    def ALGOD_ADDRESS(self) -> str:
        return self.get_secret("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")

    @property
    def ALGOD_TOKEN(self) -> str:
        default = ""
        if self.ALGORAND_NETWORK == "sandbox":
            default = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        return self.get_secret("ALGOD_TOKEN", default)

    @property
    def INDEXER_ADDRESS(self) -> str:
        return self.get_secret("INDEXER_ADDRESS", "https://testnet-indexer.algonode.cloud")

    @property
    def INDEXER_TOKEN(self) -> str:
        return self.get_secret("INDEXER_TOKEN", self.ALGOD_TOKEN)

    @property
    def SUPABASE_URL(self) -> str:
        return self.get_secret("SUPABASE_URL")

    @property
    def DATABASE_URL(self) -> str:
        return self.get_secret("DATABASE_URL")

settings = Config()
