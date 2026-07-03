from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..oidc import verify_github_oidc_token
import jwt

router = APIRouter(prefix="/api/v1/oidc", tags=["oidc"])

class OIDCVerifyRequest(BaseModel):
    token: str
    expected_repo: Optional[str] = None
    expected_workflow: Optional[str] = None
    expected_aud: str = "https://github.com/AlgoBounty"

@router.post("/verify")
async def verify_oidc(body: OIDCVerifyRequest):
    """
    Verify a GitHub Actions OIDC token.
    This endpoint can be used by GitHub Actions to prove its identity and
    the results of a workflow run.
    """
    try:
        payload = await verify_github_oidc_token(
            token=body.token,
            expected_aud=body.expected_aud,
            expected_repo=body.expected_repo,
            expected_workflow=body.expected_workflow
        )
        return {"status": "verified", "payload": payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")
