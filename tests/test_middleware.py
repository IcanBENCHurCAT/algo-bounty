import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from gateway.middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    CORSAllowlistMiddleware,
)

def test_security_headers_middleware():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/")
    def index():
        return {"status": "ok"}
        
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "X-Content-Type-Options" in res.headers

def test_request_size_limit_middleware():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)
    
    @app.post("/")
    def post_index():
        return {"status": "ok"}
        
    client = TestClient(app)
    
    # Body too large
    res = client.post("/", headers={"content-length": str(1024 * 1024 + 1)})
    assert res.status_code == 413
    assert "Request body too large" in res.json()["error"]
    
    # Invalid content length value
    res = client.post("/", headers={"content-length": "invalid"})
    assert res.status_code == 200

def test_cors_allowlist_middleware():
    app = FastAPI()
    app.add_middleware(CORSAllowlistMiddleware, allowed_origins=["https://allowed.com"])
    
    @app.get("/")
    def index():
        return {"status": "ok"}
        
    client = TestClient(app)
    
    # Origin is allowed
    res = client.get("/", headers={"origin": "https://allowed.com"})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://allowed.com"
    
    # Origin is disallowed
    res = client.get("/", headers={"origin": "https://disallowed.com"})
    assert res.status_code == 200
    assert "access-control-allow-origin" not in res.headers

    # Preflight options request (disallowed)
    res_opts = client.options("/", headers={
        "origin": "https://disallowed.com",
        "access-control-request-method": "GET"
    })
    assert res_opts.status_code == 400

    # Preflight options request (allowed)
    res_opts_allowed = client.options("/", headers={
        "origin": "https://allowed.com",
        "access-control-request-method": "GET"
    })
    assert res_opts_allowed.status_code == 200
    assert res_opts_allowed.headers.get("access-control-allow-origin") == "https://allowed.com"

def test_webhook_api_key_auth_middleware():
    from gateway.middleware import WebhookApiKeyAuthMiddleware
    
    app = FastAPI()
    app.add_middleware(WebhookApiKeyAuthMiddleware, api_key="secret_key")
    
    @app.get("/webhooks/test")
    def webhooks_test():
        return {"status": "ok"}
        
    @app.get("/api/v1/test")
    def api_test():
        return {"status": "ok"}
        
    client = TestClient(app)
    
    # 1. Non-webhook route: passes without key
    res = client.get("/api/v1/test")
    assert res.status_code == 200
    
    # 2. Webhook route: missing key -> 401
    res = client.get("/webhooks/test")
    assert res.status_code == 401
    assert "Missing or invalid X-API-Key" in res.json()["error"]
    
    # 3. Webhook route: invalid key -> 401
    res = client.get("/webhooks/test", headers={"X-API-Key": "wrong"})
    assert res.status_code == 401
    
    # 4. Webhook route: correct key -> 200
    res = client.get("/webhooks/test", headers={"X-API-Key": "secret_key"})
    assert res.status_code == 200

