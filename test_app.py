from fastapi import FastAPI
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Создаем базовое приложение
app = FastAPI()

# Настраиваем базу данных
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Создаем простую модель
class TestModel(Base):
    __tablename__ = "test"
    id = Column(String, primary_key=True)
    name = Column(String)

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Простой маршрут
@app.get("/")
def read_root():
    return {"Hello": "World"} 