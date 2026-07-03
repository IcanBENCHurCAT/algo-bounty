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
