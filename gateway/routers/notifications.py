from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import Notification
from ..auth import get_current_user
from ..dependencies import get_db

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

@router.get("")
def list_notifications(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    notifs = db.query(Notification).filter(Notification.recipient == current_user).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": n.id,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat() + "Z"
        } for n in notifs
    ]

@router.post("/{id}/read")
def read_notification(id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == id, Notification.recipient == current_user).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.commit()
    return {"status": "success"}
