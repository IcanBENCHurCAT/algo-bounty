import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gateway.routers.algorand import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_algorand_health_healthy():
    with patch("gateway.routers.algorand.algo_health_check", return_value={"algod": True, "indexer": True, "network": "testnet"}):
        res = client.get("/api/v1/algorand/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

def test_algorand_health_degraded():
    with patch("gateway.routers.algorand.algo_health_check", return_value={"algod": False, "indexer": True, "network": "testnet", "error": "down"}):
        res = client.get("/api/v1/algorand/health")
        assert res.status_code == 200
        assert res.json()["status"] == "degraded"

def test_algorand_health_exception():
    with patch("gateway.routers.algorand.algo_health_check", side_effect=Exception("crash")):
        res = client.get("/api/v1/algorand/health")
        assert res.status_code == 503

def test_algorand_balance_success():
    with patch("gateway.routers.algorand.get_account_balance", return_value={"balance": 100}):
        res = client.get("/api/v1/algorand/balance/ADDR")
        assert res.status_code == 200
        assert res.json()["balance"] == 100

def test_algorand_balance_exception():
    with patch("gateway.routers.algorand.get_account_balance", side_effect=Exception("error")):
        res = client.get("/api/v1/algorand/balance/ADDR")
        assert res.status_code == 500

def test_algorand_asset_holders_success():
    with patch("gateway.routers.algorand.get_asset_holders", return_value={"total_holders": 5}):
        res = client.get("/api/v1/algorand/asset/123/holders")
        assert res.status_code == 200
        assert res.json()["total_holders"] == 5

def test_algorand_asset_holders_exception():
    with patch("gateway.routers.algorand.get_asset_holders", side_effect=Exception("error")):
        res = client.get("/api/v1/algorand/asset/123/holders")
        assert res.status_code == 500
