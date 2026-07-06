import os
import sys
import time
import base64

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

from gateway.config import settings
from gateway.algod_client import get_algod_client, get_default_account
import algosdk
from algosdk.abi import ABIType, Method
from algosdk.transaction import (
    ApplicationCreateTxn,
    PaymentTxn,
    ApplicationNoOpTxn,
    OnComplete,
    StateSchema,
    wait_for_confirmation
)
from algosdk.logic import get_application_address

def run_lifecycle_test():
    client = get_algod_client()
    creator = get_default_account()
    
    if not creator:
        print("ERROR: PLATFORM_PRIVATE_KEY not configured in .env")
        sys.exit(1)
        
    print(f"=== Starting Testnet Lifecycle Test ===")
    print(f"Creator/Platform Address: {creator.address}")
    
    # 1. Generate a temporary worker account
    worker_private_key, worker_address = algosdk.account.generate_account()
    print(f"Temp Worker Address: {worker_address}")
    
    # 2. Fund the temporary worker account with 0.5 ALGO to cover txn fees
    params = client.suggested_params()
    params.fee = 1000
    params.flat_fee = True
    
    print("\n[Step 1] Funding temp worker account...")
    fund_worker_txn = PaymentTxn(
        sender=creator.address,
        sp=params,
        receiver=worker_address,
        amt=500_000 # 0.5 ALGO
    )
    signed_fund_worker = fund_worker_txn.sign(creator.private_key)
    txid = client.send_transaction(signed_fund_worker)
    print(f"  Sent funding txn: {txid}")
    wait_for_confirmation(client, txid, 4)
    print("  Worker funded successfully.")

    # 3. Compile the escrow contract
    from gateway.algod_client import compile_escrow_contract
    print("\n[Step 2] Compiling contract TEAL...")
    approval_teal = compile_escrow_contract("approval")
    clear_teal = compile_escrow_contract("clear")
    
    compile_resp_app = client.compile(approval_teal)
    approval_compiled = base64.b64decode(compile_resp_app.get("result", ""))

    compile_resp_clr = client.compile(clear_teal)
    clear_compiled = base64.b64decode(compile_resp_clr.get("result", ""))
    
    # 4. Deploy the application using deploy()void
    print("\n[Step 3] Deploying escrow application...")
    deploy_method = Method.from_signature("deploy()void")
    deploy_selector = deploy_method.get_selector()
    
    create_txn = ApplicationCreateTxn(
        sender=creator.address,
        sp=params,
        on_complete=OnComplete.NoOpOC,
        approval_program=approval_compiled,
        clear_program=clear_compiled,
        global_schema=StateSchema(0, 0),
        local_schema=StateSchema(0, 0),
        app_args=[deploy_selector],
        extra_pages=2
    )
    signed_create = create_txn.sign(creator.private_key)
    create_txid = client.send_transaction(signed_create)
    print(f"  Sent creation txn: {create_txid}")
    pending_info = wait_for_confirmation(client, create_txid, 4)
    app_id = pending_info.get("application-index")
    app_address = get_application_address(app_id)
    print(f"  Escrow deployed! App ID: {app_id} | App Address: {app_address}")

    # 5. Fund the application address (0.2 ALGO bounty + 0.35 ALGO MBR)
    print("\n[Step 4] Funding the contract escrow address...")
    bounty_amount = 200_000 # 0.2 ALGO
    mbr_buffer = 350_000      # 0.35 ALGO for boxes
    
    fund_txn = PaymentTxn(
        sender=creator.address,
        sp=params,
        receiver=app_address,
        amt=bounty_amount + mbr_buffer
    )
    signed_fund = fund_txn.sign(creator.private_key)
    fund_txid = client.send_transaction(signed_fund)
    print(f"  Sent contract funding txn: {fund_txid}")
    wait_for_confirmation(client, fund_txid, 4)
    print("  Contract address funded successfully.")

    # 6. Initialize bounty state (create_bounty NoOp call)
    print("\n[Step 5] Initializing bounty state...")
    create_method = Method.from_signature("create_bounty(byte[],uint64,uint64,uint64,uint64,address,address)void")
    create_selector = create_method.get_selector()
    
    bounty_id_bytes = ABIType.from_string("byte[]").encode(b"testnet_test_1")
    escrow_amount_arg = ABIType.from_string("uint64").encode(bounty_amount)
    is_hitm_arg = ABIType.from_string("uint64").encode(0)
    asset_id_arg = ABIType.from_string("uint64").encode(0)
    review_days_arg = ABIType.from_string("uint64").encode(0)
    mediator_arg = algosdk.encoding.decode_address(creator.address)
    treasury_arg = algosdk.encoding.decode_address(creator.address)
    
    app_args = [
        create_selector,
        bounty_id_bytes,
        escrow_amount_arg,
        is_hitm_arg,
        asset_id_arg,
        review_days_arg,
        mediator_arg,
        treasury_arg
    ]
    
    box_names = [
        b"state", b"mediator_address", b"treasury_address",
        b"escrow_amount", b"bounty_id", b"creator_address"
    ]
    boxes = [(app_id, name) for name in box_names]
    
    init_txn = ApplicationNoOpTxn(
        sender=creator.address,
        sp=params,
        index=app_id,
        app_args=app_args,
        boxes=boxes
    )
    signed_init = init_txn.sign(creator.private_key)
    init_txid = client.send_transaction(signed_init)
    print(f"  Sent initialization txn: {init_txid}")
    wait_for_confirmation(client, init_txid, 4)
    print("  Bounty state initialized successfully.")

    # 7. Claim bounty from worker account
    print("\n[Step 6] Claiming bounty as temp worker...")
    claim_method = Method.from_signature("claim_bounty()void")
    claim_selector = claim_method.get_selector()
    
    claim_boxes = [
        (app_id, b"state"), (app_id, b"agent_address"), (app_id, b"asset_id"),
        (app_id, b"creator_address"), (app_id, b"claim_deadline"), (app_id, b"claim_timestamp")
    ]
    
    claim_txn = ApplicationNoOpTxn(
        sender=worker_address,
        sp=params,
        index=app_id,
        app_args=[claim_selector],
        boxes=claim_boxes
    )
    signed_claim = claim_txn.sign(worker_private_key)
    claim_txid = client.send_transaction(signed_claim)
    print(f"  Sent claim txn: {claim_txid}")
    wait_for_confirmation(client, claim_txid, 4)
    print("  Bounty claimed successfully.")

    # 8. Submit work from worker account
    print("\n[Step 7] Submitting work proof as temp worker...")
    submit_method = Method.from_signature("submit_work(byte[],byte[])void")
    submit_selector = submit_method.get_selector()
    
    proof_url = ABIType.from_string("byte[]").encode(b"https://github.com/test/pull/1")
    proof_data = ABIType.from_string("byte[]").encode(b"test_verification_hash")
    
    submit_args = [
        submit_selector,
        proof_url,
        proof_data
    ]
    
    submit_boxes = [
        (app_id, b"state"),
        (app_id, b"proof_url"),
        (app_id, b"proof_data"),
        (app_id, b"is_hitm"),
        (app_id, b"agent_address"),
        (app_id, b"rejection_count")
    ]
    
    submit_txn = ApplicationNoOpTxn(
        sender=worker_address,
        sp=params,
        index=app_id,
        app_args=submit_args,
        boxes=submit_boxes
    )
    signed_submit = submit_txn.sign(worker_private_key)
    submit_txid = client.send_transaction(signed_submit)
    print(f"  Sent submission txn: {submit_txid}")
    wait_for_confirmation(client, submit_txid, 4)
    print("  Work proof submitted successfully.")

    # 9. Approve work and release payout from creator account
    print("\n[Step 8] Approving work and executing payout as creator...")
    approve_method = Method.from_signature("approve_work()void")
    approve_selector = approve_method.get_selector()
    
    approve_boxes = [
        (app_id, b"state"),
        (app_id, b"escrow_amount"),
        (app_id, b"asset_id"),
        (app_id, b"payout_type"),
        (app_id, b"treasury_address"),
        (app_id, b"agent_address"),
        (app_id, b"creator_address")
    ]
    
    # We must increase transaction fee for approve_work because it executes 2 inner payment transfers (2% fee + 98% payout)
    params.fee = 3000
    
    approve_txn = ApplicationNoOpTxn(
        sender=creator.address,
        sp=params,
        index=app_id,
        app_args=[approve_selector],
        boxes=approve_boxes,
        accounts=[worker_address]
    )
    signed_approve = approve_txn.sign(creator.private_key)
    approve_txid = client.send_transaction(signed_approve)
    print(f"  Sent approval/payout txn: {approve_txid}")
    wait_for_confirmation(client, approve_txid, 4)
    print("  Work approved & payout transaction successfully completed!")
    
    print("\n=== All Lifecycle Steps Completed Successfully on Testnet! ===")
    print(f"Bounty App ID: {app_id}")
    print(f"View app on explorer: https://testnet.algoexplorer.io/application/{app_id} (or lora.algokit.io)")

if __name__ == "__main__":
    run_lifecycle_test()
