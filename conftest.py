import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
import time

@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        yield client
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="session")
def admin_token():
    return "admin_secret_key"

@pytest.fixture(scope="session")
def user_token(client):
    response = client.post(
        "/api/v1/public/register",
        json={"name": "test_user"}
    )
    return response.json()["api_key"] 