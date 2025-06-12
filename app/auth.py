# app/auth.py

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.models import User
from app.database import get_db

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.split(" ")[1]
    user = db.query(User).filter(User.api_key == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user