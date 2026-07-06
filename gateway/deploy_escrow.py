import os
import sys

# centralize python path lookup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gateway.algod_client import deploy_escrow_on_testnet

if __name__ == "__main__":
    print("=== Running On-Chain Deployment flow ===")
    
    # Load local gateway/.env manually
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key, val = parts
                        val = val.strip().strip('"').strip("'")
                        os.environ[key.strip()] = val
                        
    # Re-import settings after loading env variables
    from gateway.config import settings
    from gateway.algod_client import get_default_account
    acc = get_default_account()
    print("LOADED PRIVATE KEY PREFIX:", settings.PLATFORM_PRIVATE_KEY[:10] if settings.PLATFORM_PRIVATE_KEY else None)
    print("LOADED ACCOUNT ADDRESS:", acc.address if acc else None)
    res = deploy_escrow_on_testnet()
    if res["success"]:
        print(f"SUCCESS: {res['message']}")
        print(f"App ID: {res['app_id']}")
        print(f"Transaction ID: {res['tx_id']}")
    else:
        print(f"FAILED: {res['error']}")
        sys.exit(1)
