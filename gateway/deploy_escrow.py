import os
import sys

# centralize python path lookup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gateway.algod_client import deploy_escrow_on_testnet

if __name__ == "__main__":
    print("=== Running On-Chain Deployment flow ===")
    res = deploy_escrow_on_testnet()
    if res["success"]:
        print(f"SUCCESS: {res['message']}")
        print(f"App ID: {res['app_id']}")
        print(f"Transaction ID: {res['tx_id']}")
    else:
        print(f"FAILED: {res['error']}")
        sys.exit(1)
