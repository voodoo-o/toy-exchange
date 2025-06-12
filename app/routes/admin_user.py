from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User as UserModel
from app.schemas import User
from app.auth import get_current_user
from app.database import get_db

router = APIRouter()

@router.delete("/{user_id}", response_model=User)
def delete_user(user_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Проверка роли ADMIN теперь реализована в get_current_user
    user = db.query(UserModel).get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return user 