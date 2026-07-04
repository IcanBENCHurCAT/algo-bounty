import pytest
import os
from unittest.mock import patch, MagicMock
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

