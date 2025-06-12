import pytest
from fastapi import status

def test_register_user(client):
    response = client.post(
        "/api/v1/public/register",
        json={"name": "test_user_1"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "api_key" in response.json()

def test_get_user_info(client, user_token):
    response = client.get(
        "/api/v1/user/info",
        headers={"Authorization": f"TOKEN {user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "test_user"

def test_admin_access(client, admin_token):
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"TOKEN {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_trading_operations(client, user_token):
    # Create a new toy
    toy_data = {
        "name": "Test Toy",
        "description": "A test toy",
        "price": 100.0
    }
    response = client.post(
        "/api/v1/user/toys",
        headers={"Authorization": f"TOKEN {user_token}"},
        json=toy_data
    )
    assert response.status_code == status.HTTP_200_OK
    toy_id = response.json()["id"]

    # List toys
    response = client.get(
        "/api/v1/public/toys",
        headers={"Authorization": f"TOKEN {user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0 