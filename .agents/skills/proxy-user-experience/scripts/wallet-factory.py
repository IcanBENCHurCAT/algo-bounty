"""
AlgoBounty Wallet Factory — Generate deterministic test wallets for multi-actor UX testing.

Each actor in a UX test scenario gets their own ed25519 keypair and Algorand address.
Wallets are deterministic (seeded from actor role names) so tests are reproducible.

Usage:
    python scripts/wallet-factory.py                    # Print all actors
    python scripts/wallet-factory.py --actor CREATOR    # Print one actor
    python scripts/wallet-factory.py --auth <base_url>  # Auth all actors and print JWTs
"""

import argparse
import hashlib
import json
import sys
import time

try:
    import nacl.signing
    from algosdk import encoding
except ImportError:
    print("ERROR: Install dependencies: pip install pynacl py-algorand-sdk", file=sys.stderr)
    sys.exit(1)

# ─── Actor Registry ────────────────────────────────────────────────────────────
# Each actor has a unique role name used as a seed for deterministic key generation.
# Add new actors here as needed.

ACTOR_ROLES = [
    "CREATOR",          # Posts bounties
    "WORKER",           # Claims and completes bounties
    "WORKER_2",         # Second worker (for competitive claims, abandoned bounties)
    "ARBITRATOR_1",     # Dispute voter 1
    "ARBITRATOR_2",     # Dispute voter 2
    "ARBITRATOR_3",     # Dispute voter 3
    "OBSERVER",         # Read-only user (no wallet, just browsing)
]


def derive_keypair(role: str) -> tuple[nacl.signing.SigningKey, str]:
    """Derive a deterministic ed25519 keypair from a role name.

    Uses SHA-512 of the role string as the 32-byte seed, ensuring
    the same role always produces the same wallet address.
    """
    seed = hashlib.sha512(f"algobounty-ux-test-{role}".encode()).digest()[:32]
    signing_key = nacl.signing.SigningKey(seed)
    verify_key = signing_key.verify_key
    address = encoding.encode_address(verify_key.encode())
    return signing_key, address


def get_all_actors() -> dict[str, dict]:
    """Generate all actor wallets."""
    actors = {}
    for role in ACTOR_ROLES:
        if role == "OBSERVER":
            actors[role] = {"address": None, "role": role, "note": "No wallet — browse-only persona"}
            continue
        sk, addr = derive_keypair(role)
        actors[role] = {
            "address": addr,
            "role": role,
            "private_key_hex": sk.encode().hex(),
            "public_key_hex": sk.verify_key.encode().hex(),
        }
    return actors


def authenticate_actor(base_url: str, role: str, signing_key: nacl.signing.SigningKey, address: str) -> str | None:
    """Authenticate an actor against the gateway and return a JWT.

    This performs the same challenge-response flow as the frontend:
    1. POST /api/v1/auth/request → get challenge
    2. Sign the challenge bytes with ed25519
    3. POST /api/v1/auth/verify → get JWT

    NOTE: The gateway's verify endpoint tries raw byte verification first
    (via algosdk.util.verify_bytes). We sign the raw challenge string,
    which matches the ARC-60 / raw-bytes verification path.
    """
    try:
        import requests
    except ImportError:
        print("ERROR: Install requests: pip install requests", file=sys.stderr)
        return None

    # Step 1: Request challenge
    resp = requests.post(
        f"{base_url}/api/v1/auth/request",
        json={"address": address},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  [{role}] Auth request failed: {resp.status_code} {resp.text}", file=sys.stderr)
        return None

    challenge = resp.json()["challenge"]

    # Step 2: Sign the challenge bytes
    message_bytes = b"MX" + challenge.encode("utf-8")
    signed = signing_key.sign(message_bytes)
    signature_b64 = __import__("base64").b64encode(signed.signature).decode()

    # Step 3: Verify signature and get JWT
    resp = requests.post(
        f"{base_url}/api/v1/auth/verify",
        json={
            "address": address,
            "signature": signature_b64,
            "challenge": challenge,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  [{role}] Auth verify failed: {resp.status_code} {resp.text}", file=sys.stderr)
        return None

    data = resp.json()
    return data["jwt"]


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="AlgoBounty Wallet Factory")
    parser.add_argument("--actor", type=str, help="Print info for a specific actor role")
    parser.add_argument("--auth", type=str, metavar="BASE_URL",
                        help="Authenticate all actors against the gateway and return JWTs")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    actors = get_all_actors()

    if args.auth:
        if not args.json:
            print(f"Authenticating actors against {args.auth}...\n")
        results = {}
        for role, info in actors.items():
            if role == "OBSERVER":
                results[role] = {"address": None, "jwt": None, "role": role}
                continue
            sk, addr = derive_keypair(role)
            jwt = authenticate_actor(args.auth, role, sk, addr)
            results[role] = {
                "address": addr,
                "jwt": jwt,
                "role": role,
                "authenticated": jwt is not None,
            }
            status = "✓" if jwt else "✗"
            if not args.json:
                print(f"  {status} {role}: {addr[:8]}...{addr[-4:]}")
            else:
                print(f"  {status} {role}: {addr[:8]}...{addr[-4:]}", file=sys.stderr)

        if args.json:
            print(json.dumps(results, indent=2))
        return

    if args.actor:
        role = args.actor.upper()
        if role not in actors:
            print(f"Unknown actor: {role}. Available: {', '.join(ACTOR_ROLES)}", file=sys.stderr)
            sys.exit(1)
        info = actors[role]
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"Role:    {info['role']}")
            print(f"Address: {info.get('address', 'N/A')}")
        return

    # Print all actors
    if args.json:
        print(json.dumps(actors, indent=2))
    else:
        print("AlgoBounty Test Actors\n" + "=" * 60)
        for role, info in actors.items():
            addr = info.get("address", "N/A (no wallet)")
            print(f"  {role:15s}  {addr}")


if __name__ == "__main__":
    main()
