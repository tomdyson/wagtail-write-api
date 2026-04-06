import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.authtoken.models import Token


@pytest.mark.django_db
class TestTokenAuth:
    def test_valid_token_authenticates(self, api_client, admin_user, admin_token):
        response = api_client.get(
            "/api/write/v1/pages/",
            HTTP_AUTHORIZATION=f"Bearer {admin_token}",
        )
        assert response.status_code == 200

    def test_invalid_token_returns_401(self, api_client):
        response = api_client.get(
            "/api/write/v1/pages/",
            HTTP_AUTHORIZATION="Bearer invalid-token-here",
        )
        assert response.status_code == 401

    def test_missing_auth_returns_401(self, api_client):
        response = api_client.get("/api/write/v1/pages/")
        assert response.status_code == 401

    def test_inactive_user_returns_401(self, api_client, db):
        user = User.objects.create_user("inactive", "inactive@example.com", "password")
        user.is_active = False
        user.save()
        token = Token.objects.create(user=user)
        response = api_client.get(
            "/api/write/v1/pages/",
            HTTP_AUTHORIZATION=f"Bearer {token.key}",
        )
        assert response.status_code == 401
