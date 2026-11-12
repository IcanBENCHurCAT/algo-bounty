import os
import logging
from typing import Optional

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
        if isinstance(val, str):
            val = val.strip()
        if not val and not default:
            logger.warning(f"Secret {key} is not set in environment.")
        return val

    @property
    def SECRET_KEY(self) -> str:
        val = self.get_secret("SECRET_KEY")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("SECRET_KEY must be set in testnet/mainnet")
        return val

    @property
    def GITHUB_TOKEN(self) -> str:
        val = self.get_secret("GITHUB_TOKEN")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("GITHUB_TOKEN must be set in testnet/mainnet")
        return val

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
    def GITHUB_INSTALLATION_ID(self) -> str:
        return self.get_secret("GITHUB_INSTALLATION_ID")

    @property
    def PLATFORM_PRIVATE_KEY(self) -> str:
        val = self.get_secret("PLATFORM_PRIVATE_KEY")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("PLATFORM_PRIVATE_KEY must be set in testnet/mainnet")
        return val

    @property
    def GITHUB_WEBHOOK_SECRET(self) -> str:
        val = self.get_secret("GITHUB_WEBHOOK_SECRET")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("GITHUB_WEBHOOK_SECRET must be set in testnet/mainnet")
        return val

    @property
    def WEBHOOK_API_KEY(self) -> str:
        val = self.get_secret("WEBHOOK_API_KEY")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("WEBHOOK_API_KEY must be set in testnet/mainnet")
        return val

    @property
    def ALGORAND_NETWORK(self) -> str:
        return self.get_secret("ALGORAND_NETWORK", "testnet")

    @property
    def TREASURY_ADDRESS(self) -> str:
        addr = self.get_secret("TREASURY_ADDRESS")
        if addr:
            return addr
        from gateway.algod_client import get_default_account
        acct = get_default_account()
        return acct.address if acct else ""

    @property
    def SUPABASE_URL(self) -> str:
        return self.get_secret("SUPABASE_URL")

    @property
    def DATABASE_URL(self) -> str:
        return self.get_secret("DATABASE_URL")

    @property
    def ESCROW_TEMPLATE_APP_ID(self) -> int:
        val = self.get_secret("ESCROW_TEMPLATE_APP_ID", "0")
        try:
            return int(val)
        except ValueError:
            return 0

    @property
    def ADMIN_ADDRESS(self) -> str:
        addr = self.get_secret("ADMIN_ADDRESS")
        if addr:
            return addr
        return self.TREASURY_ADDRESS

    REQUIRE_SCREENING: bool = False
    _require_screening: Optional[bool] = None

    @property
    def REQUIRE_SCREENING(self) -> bool:
        if self._require_screening is not None:
            return self._require_screening
        val = self.get_secret("REQUIRE_SCREENING", "false")
        return str(val).strip().lower() in ("true", "1", "yes")

    @REQUIRE_SCREENING.setter
    def REQUIRE_SCREENING(self, val: bool):
        self._require_screening = bool(val)

    @REQUIRE_SCREENING.deleter
    def REQUIRE_SCREENING(self):
        self._require_screening = None

    @property
    def KYA_SERVICE_URL(self) -> str:
        return self.get_secret("KYA_SERVICE_URL", "http://localhost:8001")

    @property
    def KYA_API_KEY(self) -> str:
        return self.get_secret("KYA_API_KEY", "")

REQUIRE_SCREENING: bool = False

settings = Config()
