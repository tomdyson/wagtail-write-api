import json

import pytest
from django.contrib.auth.models import User

from wagtail_write_api.models import ApiToken


@pytest.fixture
def user_with_password(db):
    user = User.objects.create_user("testuser", "test@example.com", "testpass123")
    return user


class TestObtainToken:
    def test_valid_credentials_returns_token(self, api_client, user_with_password):
        response = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["username"] == "testuser"
        assert len(data["token"]) == 40

    def test_returns_existing_token_on_repeat(self, api_client, user_with_password):
        response1 = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )
        response2 = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )
        assert response1.json()["token"] == response2.json()["token"]

    def test_invalid_password_returns_401(self, api_client, user_with_password):
        response = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser", "password": "wrong"}),
            content_type="application/json",
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "authentication_failed"

    def test_nonexistent_user_returns_401(self, api_client, db):
        response = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "nobody", "password": "pass"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_inactive_user_returns_401(self, api_client, user_with_password):
        user_with_password.is_active = False
        user_with_password.save()
        response = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_missing_fields_returns_422(self, api_client, db):
        response = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser"}),
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_no_auth_required(self, api_client, user_with_password):
        """The token endpoint must be accessible without a Bearer token."""
        response = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )
        assert response.status_code == 200

    def test_user_with_existing_token(self, api_client, user_with_password):
        """If the user already has a token, return it rather than creating a new one."""
        existing = ApiToken.objects.create(user=user_with_password)
        response = api_client.post(
            "/api/write/v1/auth/token/",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["token"] == existing.key
