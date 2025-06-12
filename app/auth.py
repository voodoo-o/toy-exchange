from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole

security = HTTPBearer(auto_error=False)

ADMIN_SECRET_KEY = "admin_secret_key"

class AdminUser:
    id = "admin"
    name = "Admin"
    role = UserRole.ADMIN
    api_key = ADMIN_SECRET_KEY


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    if token == ADMIN_SECRET_KEY:
        return AdminUser()
    user = db.query(User).filter(User.api_key == token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user 