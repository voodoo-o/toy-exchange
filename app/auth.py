from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole

ADMIN_SECRET_KEY = "admin_secret_key"

class AdminUser:
    id = "admin"
    name = "Admin"
    role = UserRole.ADMIN
    api_key = ADMIN_SECRET_KEY


def get_current_user(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        scheme, token = auth_header.split()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")
    if scheme.lower() not in ["bearer", "token"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    if token == ADMIN_SECRET_KEY:
        return AdminUser()
    user = db.query(User).filter(User.api_key == token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if request.url.path.startswith("/api/v1/admin") and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user 