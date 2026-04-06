import pytest
from django.test import Client


@pytest.mark.django_db
def test_app_loads():
    """The wagtail_write_api app loads without errors."""
    from wagtail_write_api import __version__

    assert __version__ == "0.1.0"


@pytest.mark.django_db
def test_docs_endpoint_reachable():
    """The API docs endpoint returns 200."""
    client = Client()
    response = client.get("/api/write/v1/docs")
    assert response.status_code == 200
