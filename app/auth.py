# app/auth.py

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.models import User, UserRole
from app.database import get_db
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем админский ключ из переменных окружения или используем значение по умолчанию
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin_secret_key")

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid authorization header"
        )

    token_parts = authorization.split(" ")
    if len(token_parts) != 2 or not token_parts[1]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid token format"
        )
        
    token = token_parts[1]
    
    try:
        # Проверка на админский ключ
        if token == ADMIN_API_KEY:
            # Проверяем существование админа
            admin = db.query(User).filter(User.api_key == ADMIN_API_KEY).first()
            if not admin:
                # Создаем админа, если его нет
                admin = User(
                    name="System Admin",
                    api_key=ADMIN_API_KEY,
                    role=UserRole.ADMIN
                )
                db.add(admin)
                db.commit()
                db.refresh(admin)
            return admin
        
        # Обычная проверка пользователя
        user = db.query(User).filter(User.api_key == token).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Invalid token"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required"
        )
    return current_user