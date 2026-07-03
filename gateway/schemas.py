import re
from typing import Optional
from pydantic import BaseModel, field_validator, EmailStr

# ── Input sanitization utilities ─────────────────────────────────

def sanitize_string(value: str, max_length: int = 10000) -> str:
    """Strip whitespace, enforce length limits, reject null bytes."""
    if not isinstance(value, str):
        return str(value)
    value = value.strip()
    value = value.replace("\x00", "")  # null byte injection prevention
    return value[:max_length]


def sanitize_sql_like(value: str, max_length: int = 10000) -> str:
    """Escape SQL LIKE wildcards to prevent LIKE injection."""
    value = sanitize_string(value, max_length)
    value = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return value


def validate_url(value: str) -> str:
    """Basic URL format validation for repo URLs, PR URLs, etc."""
    value = sanitize_string(value, 2048)
    if not value:
        raise ValueError("URL cannot be empty")
    if not re.match(r"^https?://", value):
        raise ValueError("URL must start with http:// or https://")
    return value


# ── Pydantic Schemas
class AuthRequest(BaseModel):
    address: str

    @field_validator("address")
    @classmethod
    def sanitize_address(cls, v):
        return sanitize_string(v, 64)

class AuthVerify(BaseModel):
    address: str
    signature: str
    challenge: str

    @field_validator("address")
    @classmethod
    def sanitize_address(cls, v):
        return sanitize_string(v, 64)

    @field_validator("signature", "challenge")
    @classmethod
    def sanitize_hex(cls, v):
        return sanitize_string(v, 512)

class BountyCreate(BaseModel):
    description: str
    amount: int
    asset_id: int = 0
    hitm: bool = False
    repo_url: str
    karma_requirement: int = 0
    github_issue: Optional[int] = None
    hitm_review_days: int = 7

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v):
        return sanitize_string(v, 10000)

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v):
        return validate_url(v)

class BountyClaim(BaseModel):
    signed_txn: str

class WorkSubmit(BaseModel):
    pr_url: str
    proof_data: Optional[dict] = None
    signed_txn: Optional[str] = None

    @field_validator("pr_url")
    @classmethod
    def validate_pr_url(cls, v):
        return validate_url(v)

class WorkApprove(BaseModel):
    signed_txn: Optional[str] = None

class WorkReject(BaseModel):
    reason: str
    signed_txn: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def sanitize_reason(cls, v):
        return sanitize_string(v, 2000)

class DisputeCreate(BaseModel):
    reason: str
    signed_txn: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def sanitize_reason(cls, v):
        return sanitize_string(v, 2000)


# ── Webhook & Notification schemas ─────────────────────────────────

class WebhookContentValidate(BaseModel):
    """Minimal model to validate webhook request content-type."""
    content_type: str = "application/json"

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        if "application/json" not in v.lower():
            raise ValueError("Only application/json is accepted")
        return v


class NotificationRead(BaseModel):
    """Schema for marking a notification as read."""
    id: int

    @field_validator("id")
    @classmethod
    def validate_id(cls, v):
        if v < 1:
            raise ValueError("Notification ID must be positive")
        return v
