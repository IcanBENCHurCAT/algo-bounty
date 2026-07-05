import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
from gateway import algod_client

def test_is_sandbox():
    # Use patch.object to ensure we are changing the actual variable used by the function
    with patch.object(algod_client, "NODE_ENV", "sandbox"):
        assert algod_client.is_sandbox() is True
    with patch.object(algod_client, "NODE_ENV", "testnet"):
        assert algod_client.is_sandbox() is False

def test_get_algod_client():
    with patch("algosdk.v2client.algod.AlgodClient") as mock_client:
        client = algod_client.get_algod_client()
        assert client is not None
        mock_client.assert_called_once()

def test_get_default_account_no_key():
    with patch("gateway.algod_client.settings") as mock_settings:
        mock_settings.PLATFORM_PRIVATE_KEY = ""
        acc = algod_client.get_default_account()
        assert acc is None

def test_get_default_account_with_key():
    with patch("gateway.algod_client.settings") as mock_settings, \
         patch("algosdk.account.address_from_private_key", return_value="ADDR123"):
        mock_settings.PLATFORM_PRIVATE_KEY = "some fake key"
        acc = algod_client.get_default_account()
        assert acc.address == "ADDR123"
        assert acc.private_key == "some fake key"

def test_get_indexer_client():
    with patch("algosdk.v2client.indexer.IndexerClient") as mock_indexer:
        client = algod_client.get_indexer_client()
        assert client is not None
        mock_indexer.assert_called_once()

def test_health_check_success():
    mock_ac = MagicMock()
    mock_ac.status.return_value = {"last-round": 100, "version": "v1", "network": "testnet"}
    mock_ic = MagicMock()
    mock_ic.status.return_value = {"last-round": 100, "version": "v1"}
    
    with patch("gateway.algod_client.get_algod_client", return_value=mock_ac), \
         patch("gateway.algod_client.get_indexer_client", return_value=mock_ic):
        hc = algod_client.health_check()
        assert hc["algod"] is True
        assert hc["indexer"] is True
        assert hc["error"] is None

def test_health_check_error():
    with patch("gateway.algod_client.get_algod_client", side_effect=Exception("algod down")):
        hc = algod_client.health_check()
        assert hc["algod"] is False
        assert hc["error"] == "algod down"

def test_get_account_balance_success():
    mock_ac = MagicMock()
    mock_ac.account_info.return_value = {"amount": 2000000, "assets": [{"asset-id": 12, "amount": 100}]}
    
    with patch("gateway.algod_client.get_algod_client", return_value=mock_ac):
        res = algod_client.get_account_balance("ADDR")
        assert res["balance"] == 2000000
        assert res["balance_algo"] == 2.0
        assert len(res["assets"]) == 1

def test_get_account_balance_error():
    with patch("gateway.algod_client.get_algod_client", side_effect=Exception("error")):
        res = algod_client.get_account_balance("ADDR")
        assert res["balance"] == 0
        assert "error" in res

def test_get_transaction_status_confirmed():
    mock_ic = MagicMock()
    mock_ic.transaction_by_id.return_value = {"confirmed-round": 10}
    with patch("gateway.algod_client.get_indexer_client", return_value=mock_ic):
        res = algod_client.get_transaction_status("tx_id")
        assert res["confirmed"] is True
        assert res["transaction"] == {"confirmed-round": 10}

def test_get_transaction_status_pending():
    mock_ic = MagicMock()
    mock_ic.transaction_by_id.side_effect = Exception("not confirmed yet")
    mock_ic.pending_transaction_by_id.return_value = {"pool-error": ""}
    with patch("gateway.algod_client.get_indexer_client", return_value=mock_ic):
        res = algod_client.get_transaction_status("tx_id")
        assert res["confirmed"] is False
        assert res["pending"] is True
        assert res["transaction"] == {"pool-error": ""}

def test_get_transaction_status_failure():
    mock_ic = MagicMock()
    mock_ic.transaction_by_id.side_effect = Exception("err")
    mock_ic.pending_transaction_by_id.side_effect = Exception("err2")
    with patch("gateway.algod_client.get_indexer_client", return_value=mock_ic):
        res = algod_client.get_transaction_status("tx_id")
        assert res["confirmed"] is False
        assert "error" in res

def test_get_asset_holders_success():
    mock_ic = MagicMock()
    mock_ic.get_asset_balances.return_value = {"balances": [{"address": "ADDR1", "amount": 100}]}
    with patch("gateway.algod_client.get_indexer_client", return_value=mock_ic):
        res = algod_client.get_asset_holders(123)
        assert res["total_holders"] == 1
        assert res["holders"][0]["address"] == "ADDR1"

def test_get_asset_holders_error():
    mock_ic = MagicMock()
    mock_ic.get_asset_balances.side_effect = Exception("err")
    with patch("gateway.algod_client.get_indexer_client", return_value=mock_ic):
        res = algod_client.get_asset_holders(123)
        assert res["total_holders"] == 0
        assert "error" in res

def test_compile_escrow_contract_subprocess_ok():
    with patch("gateway.algod_client.ESCROW_TEAL", None), \
         patch("subprocess.run") as mock_sub, \
         patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="approval_teal")):
        mock_sub.return_value = MagicMock(returncode=0)
        res = algod_client.compile_escrow_contract()
        assert res == "approval_teal"

def test_compile_escrow_contract_precompiled_ok():
    with patch("gateway.algod_client.ESCROW_TEAL", None), \
         patch("subprocess.run", side_effect=FileNotFoundError()), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="precompiled_teal")):
        res = algod_client.compile_escrow_contract()
        assert res == "precompiled_teal"

def test_compile_escrow_contract_docstring_fallback():
    with patch("gateway.algod_client.ESCROW_TEAL", None), \
         patch("subprocess.run", side_effect=FileNotFoundError()), \
         patch("pathlib.Path.exists", return_value=False), \
         patch("builtins.open", mock_open(read_data='"""doc"""\ncode_body')):
        res = algod_client.compile_escrow_contract()
        assert "code_body" in res

def test_deploy_escrow_on_testnet_sandbox_error():
    with patch("gateway.algod_client.is_sandbox", return_value=True):
        res = algod_client.deploy_escrow_on_testnet()
        assert res["success"] is False
        assert "Cannot deploy on sandbox" in res["error"]

def test_deploy_escrow_on_testnet_no_account():
    with patch("gateway.algod_client.is_sandbox", return_value=False), \
         patch("gateway.algod_client.get_default_account", return_value=None):
        res = algod_client.deploy_escrow_on_testnet()
        assert res["success"] is False
        assert "PLATFORM_PRIVATE_KEY" in res["error"]

def test_deploy_escrow_on_testnet_success():
    import algosdk.transaction
    import algosdk.account
    from algosdk.transaction import SuggestedParams
    pk, addr = algosdk.account.generate_account()
    
    class MockAccount:
        def __init__(self, private_key, address):
            self.private_key = private_key
            self.address = address
            
    mock_account = MockAccount(pk, addr)
    mock_ac = MagicMock()
    mock_ac.compile.return_value = {"result": "YQ=="}
    # Genesis hash must be 32 bytes base64 encoded
    mock_ac.suggested_params.return_value = SuggestedParams(fee=1000, first=1, last=100, gh="Z2VuZXNpc19oYXNoXzMyX2J5dGVzX2xvbmdfcGFkZGVk")
    mock_ac.send_transaction.return_value = "tx_id"
    
    with patch("gateway.algod_client.is_sandbox", return_value=False), \
         patch("gateway.algod_client.get_default_account", return_value=mock_account), \
         patch("gateway.algod_client.compile_escrow_contract", return_value="teal_code"), \
         patch("gateway.algod_client.get_algod_client", return_value=mock_ac), \
         patch("algosdk.transaction.wait_for_confirmation", return_value={"application-index": 12345}):
        res = algod_client.deploy_escrow_on_testnet()
        assert res["success"] is True, res["error"]
        assert res["app_id"] == 12345
        assert res["tx_id"] == "tx_id"

def test_send_signed_transaction_success():
    mock_ac = MagicMock()
    mock_ac.send_raw_transaction.return_value = "txid123"
    with patch("gateway.algod_client.get_algod_client", return_value=mock_ac):
        res = algod_client.send_signed_transaction("YQ==") # base64 for "a"
        assert res == "txid123"
        mock_ac.send_raw_transaction.assert_called_once()

def test_send_signed_transaction_error():
    mock_ac = MagicMock()
    mock_ac.send_raw_transaction.side_effect = Exception("broadcast error")
    with patch("gateway.algod_client.get_algod_client", return_value=mock_ac):
        with pytest.raises(Exception, match="broadcast error"):
            algod_client.send_signed_transaction("YQ==")


