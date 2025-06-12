from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User as UserModel
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/v1/admin/user", tags=["admin", "user"])

@router.delete("/{user_id}")
def delete_user(user_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Forbidden")
    user = db.query(UserModel).get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return {"success": True}