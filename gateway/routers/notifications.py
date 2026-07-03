from datetime import UTC
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from ..database import Notification
from ..auth import get_current_user
from ..dependencies import get_db
from ..schemas import sanitize_string

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

@router.get("", summary="List notifications", description="Retrieve all notifications for the currently authenticated agent, ordered by creation date (newest first).")
def list_notifications(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    notifs = db.query(Notification).filter(Notification.recipient == current_user).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": n.id,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
        } for n in notifs
    ]

@router.post("/{id}/read", summary="Mark notification as read", description="Update the status of a specific notification to 'read'.")
def read_notification(id: int = Path(..., ge=1), db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """Mark a notification as read.
    
    Input validation: id must be a positive integer (enforced via Path constraint).
    """
    # Input sanitization
    sanitized_user = sanitize_string(current_user, 64)

    notif = db.query(Notification).filter(Notification.id == id, Notification.recipient == sanitized_user).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.commit()
    return {"status": "success"}
