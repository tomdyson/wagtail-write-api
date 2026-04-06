import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.authtoken.models import Token
from wagtail.models import Page, Site


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser("admin", "admin@example.com", "password")
    return user


@pytest.fixture
def admin_token(admin_user):
    token, _ = Token.objects.get_or_create(user=admin_user)
    return token.key


@pytest.fixture
def auth_header(admin_token):
    return {"HTTP_AUTHORIZATION": f"Bearer {admin_token}"}


@pytest.fixture
def home_page(db):
    # Wagtail's initial migration creates a root page at depth=1
    # and a "Welcome to Wagtail" page at depth=2.
    # We'll use the root and add our home page.
    root = Page.objects.filter(depth=1).first()
    home = root.add_child(title="Home", slug="home-test")
    Site.objects.update_or_create(
        is_default_site=True,
        defaults={"hostname": "localhost", "root_page": home},
    )
    return home
