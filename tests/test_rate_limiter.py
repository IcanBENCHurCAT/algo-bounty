import os
import time
from unittest.mock import patch
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from gateway.rate_limiter import RateLimitMiddleware, _get_client_ip, _request_log, _connection_log

def test_rate_limiter_ip_extraction():
    # Test _get_client_ip helper with various headers
    class MockRequest:
        def __init__(self, headers, client=None):
            self.headers = headers
            self.client = client
            
    req1 = MockRequest({"x-forwarded-for": "1.2.3.4, 5.6.7.8"})
    assert _get_client_ip(req1) == "1.2.3.4"
    
    req2 = MockRequest({"x-real-ip": "9.9.9.9"})
    assert _get_client_ip(req2) == "9.9.9.9"
    
    class HostClient:
        def __init__(self, host):
            self.host = host
            
    req3 = MockRequest({}, HostClient("5.5.5.5"))
    assert _get_client_ip(req3) == "5.5.5.5"
    
    req4 = MockRequest({})
    assert _get_client_ip(req4) == "unknown"

def test_rate_limiter_middleware_bypass():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    
    @app.get("/api/v1/test-limiter")
    def test_route():
        return {"status": "ok"}
        
    client = TestClient(app)
    
    # 1. With TESTING="True", no rate limiting should apply
    with patch.dict(os.environ, {"TESTING": "True"}):
        for _ in range(10):
            res = client.get("/api/v1/test-limiter")
            assert res.status_code == 200
            
    # 2. With TESTING="False", rate limiting applies.
    # The default rule for /api/v1/ GET is 100 req/min. Let's mock a strict rule to trigger limit.
    # We can inject a mock rule into the middleware compiled rules or mock time.
    from gateway.rate_limiter import _RULES_COMPILED
    import re
    strict_rule = (re.compile(r"^/api/v1/test-limiter$"), 2, 60, None, None)
    
    # Let's clean the log first
    _request_log.clear()
    
    with patch("gateway.rate_limiter._RULES_COMPILED", [strict_rule]):
        with patch.dict(os.environ, {"TESTING": "False"}):
            # First request - OK
            res = client.get("/api/v1/test-limiter")
            assert res.status_code == 200
            assert res.headers.get("X-RateLimit-Remaining") == "1"
            
            # Second request - OK
            res = client.get("/api/v1/test-limiter")
            assert res.status_code == 200
            assert res.headers.get("X-RateLimit-Remaining") == "0"
            
            # Third request - Throttled (429)
            res = client.get("/api/v1/test-limiter")
            assert res.status_code == 429
            assert "Rate limit exceeded" in res.json()["error"]
            
            # Forged Bearer token now falls back to rate limit
            res = client.get("/api/v1/test-limiter", headers={"Authorization": "Bearer aaa.bbb.ccc"})
            assert res.status_code == 429
            assert "Rate limit exceeded" in res.json()["error"]

def test_rate_limiter_valid_jwt_bypass():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test-limiter")
    def test_route():
        return {"status": "ok"}

    client = TestClient(app)

    from gateway.rate_limiter import _RULES_COMPILED
    from gateway.auth import create_jwt_token
    import re
    strict_rule = (re.compile(r"^/api/v1/test-limiter$"), 0, 60, None, None)

    _request_log.clear()

    with patch("gateway.rate_limiter._RULES_COMPILED", [strict_rule]):
        with patch.dict(os.environ, {"TESTING": "False"}):
            # Without token, hits limit of 0 and gets 429
            res = client.get("/api/v1/test-limiter")
            assert res.status_code == 429

            # With real token, bypasses limit of 0
            real_token = create_jwt_token("TEST_ADDR")
            res = client.get("/api/v1/test-limiter", headers={"Authorization": f"Bearer {real_token}"})
            assert res.status_code == 200

def test_rate_limiter_expired_jwt_no_bypass():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test-limiter")
    def test_route():
        return {"status": "ok"}

    client = TestClient(app)

    from gateway.rate_limiter import _RULES_COMPILED
    from gateway.auth import create_jwt_token
    import re
    strict_rule = (re.compile(r"^/api/v1/test-limiter$"), 0, 60, None, None)

    _request_log.clear()

    with patch("gateway.rate_limiter._RULES_COMPILED", [strict_rule]):
        with patch.dict(os.environ, {"TESTING": "False"}):
            # Mock time to create an already expired token
            with patch("time.time", return_value=0):
                # Token created with iat=0, exp=86400.
                # To make it expired now (assuming now is > 86400), we just generate it,
                # then use it without the time mock so jwt.decode uses real current time.
                expired_token = create_jwt_token("TEST_ADDR")

            res = client.get("/api/v1/test-limiter", headers={"Authorization": f"Bearer {expired_token}"})
            assert res.status_code == 429
            assert "Rate limit exceeded" in res.json()["error"]

def test_rate_limiter_sse_connections():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    
    @app.get("/api/v1/events")
    def events_route():
        return {"events": []}
        
    client = TestClient(app)
    
    # SSE events connections rule: limit 2
    from gateway.rate_limiter import _RULES_COMPILED
    import re
    sse_rule = (re.compile(r"^/api/v1/events$"), 2, 60, "GET", "connections")
    
    _connection_log.clear()
    
    with patch("gateway.rate_limiter._RULES_COMPILED", [sse_rule]):
        with patch.dict(os.environ, {"TESTING": "False"}):
            # Seed connection log for testclient IP
            _connection_log["testclient"] = 2
            _connection_log["127.0.0.1"] = 2
            
            # Connection exceeds 2 limit
            res = client.get("/api/v1/events")
            assert res.status_code == 429
            assert "Rate limit exceeded" in res.json()["error"]

def test_rate_limiter_more_rules():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    
    @app.get("/api/v1/non-matching-route")
    def no_match():
        return {"status": "ok"}
        
    @app.post("/api/v1/events")
    def post_events():
        return {"status": "ok"}
        
    @app.get("/api/v1/events")
    def sse_ok():
        return {"status": "ok"}
        
    client = TestClient(app)
    
    # 1. No rule matched
    with patch.dict(os.environ, {"TESTING": "False"}):
        res = client.get("/api/v1/non-matching-route")
        assert res.status_code == 200

    from gateway.rate_limiter import _RULES_COMPILED
    import re
    sse_rule = (re.compile(r"^/api/v1/events$"), 2, 60, "GET", "connections")
    
    with patch("gateway.rate_limiter._RULES_COMPILED", [sse_rule]):
        with patch.dict(os.environ, {"TESTING": "False"}):
            _connection_log.clear()
            
            # 2. Method mismatch (rules say GET only, we send POST)
            res = client.post("/api/v1/events")
            assert res.status_code == 200
            
            # 3. Connection is allowed (count increments and decrements correctly)
            res = client.get("/api/v1/events")
            assert res.status_code == 200
            assert _connection_log.get("testclient", 0) == 0 # decremented back to 0 in finally block

