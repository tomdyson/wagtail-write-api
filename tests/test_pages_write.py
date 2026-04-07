import json

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client
from wagtail.models import GroupPagePermission, Page

from testapp.models import BlogIndexPage, BlogPage, EventPage, SimplePage


@pytest.fixture
def blog_tree(home_page):
    blog_index = home_page.add_child(
        instance=BlogIndexPage(title="Blog", slug="blog", intro="Blog intro")
    )
    blog_index.save_revision().publish()
    return {"home": home_page, "blog_index": blog_index}


@pytest.mark.django_db
class TestCreatePage:
    def test_create_simple_page(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {"type": "testapp.SimplePage", "parent": home_page.id, "title": "New Page"}
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Page"
        assert data["id"] is not None

    def test_create_auto_generates_slug(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {"type": "testapp.SimplePage", "parent": home_page.id, "title": "My New Page"}
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-new-page"

    def test_create_as_draft_by_default(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {"type": "testapp.SimplePage", "parent": home_page.id, "title": "Draft"}
            ),
            content_type="application/json",
            **auth_header,
        )
        data = response.json()
        assert data["meta"]["live"] is False

    def test_create_with_publish_action(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.SimplePage",
                    "parent": home_page.id,
                    "title": "Published",
                    "action": "publish",
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        data = response.json()
        assert data["meta"]["live"] is True

    def test_create_blog_page_with_authors(self, api_client, auth_header, blog_tree):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.BlogPage",
                    "parent": blog_tree["blog_index"].id,
                    "title": "Post with Authors",
                    "authors": [
                        {"name": "Alice", "role": "Writer"},
                        {"name": "Bob", "role": "Editor"},
                    ],
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["authors"]) == 2
        assert data["authors"][0]["name"] == "Alice"

    def test_create_with_parent_path(self, api_client, auth_header, home_page):
        """Accept a URL path string for the parent field."""
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps({"type": "testapp.SimplePage", "parent": "/", "title": "Path Parent"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Path Parent"
        assert data["meta"]["parent_id"] == home_page.id

    def test_create_with_nested_parent_path(self, api_client, auth_header, blog_tree):
        """Accept a nested path like /blog/ for the parent field."""
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.BlogPage",
                    "parent": "/blog/",
                    "title": "Path Nested",
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["meta"]["parent_id"] == blog_tree["blog_index"].id

    def test_create_with_invalid_parent_path_returns_422(self, api_client, auth_header, home_page):
        """A path that doesn't resolve returns 422."""
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.SimplePage",
                    "parent": "/nonexistent/path/",
                    "title": "Bad Path",
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 422
        data = response.json()
        assert "No page found at path" in data["message"]

    def test_create_without_auth_returns_401(self, api_client, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {"type": "testapp.SimplePage", "parent": home_page.id, "title": "No Auth"}
            ),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_create_invalid_type_under_parent_returns_422(
        self, api_client, auth_header, home_page
    ):
        """BlogPage can only go under BlogIndexPage, not directly under home."""
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {"type": "testapp.BlogPage", "parent": home_page.id, "title": "Wrong Parent"}
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 422

    def test_create_invalid_streamfield_data_returns_422(self, api_client, auth_header, blog_tree):
        """Passing a dict instead of a list for a StreamField returns 422, not 500."""
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.BlogPage",
                    "parent": blog_tree["blog_index"].id,
                    "title": "Bad StreamField",
                    "body": {"format": "markdown", "content": "This is wrong"},
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"

    def test_create_malformed_json_returns_422(self, api_client, auth_header):
        """Malformed JSON in request body returns 422, not 500."""
        response = api_client.post(
            "/api/write/v1/pages/",
            data="not valid json{",
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"
        assert "Invalid JSON" in data["message"]


@pytest.mark.django_db
class TestUpdatePage:
    def test_update_title(self, api_client, auth_header, home_page):
        page = home_page.add_child(
            instance=SimplePage(title="Original", slug="original", body="Body")
        )
        page.save_revision()

        response = api_client.patch(
            f"/api/write/v1/pages/{page.id}/",
            data=json.dumps({"title": "Updated Title"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_creates_revision(self, api_client, auth_header, home_page):
        page = home_page.add_child(
            instance=SimplePage(title="Original", slug="rev-test", body="Body")
        )
        page.save_revision()
        rev_count = page.revisions.count()

        api_client.patch(
            f"/api/write/v1/pages/{page.id}/",
            data=json.dumps({"title": "Updated"}),
            content_type="application/json",
            **auth_header,
        )
        page.refresh_from_db()
        assert page.revisions.count() == rev_count + 1

    def test_partial_update_preserves_other_fields(self, api_client, auth_header, home_page):
        page = home_page.add_child(
            instance=SimplePage(title="Original", slug="partial", body="Keep this body")
        )
        page.save_revision()

        api_client.patch(
            f"/api/write/v1/pages/{page.id}/",
            data=json.dumps({"title": "New Title"}),
            content_type="application/json",
            **auth_header,
        )
        response = api_client.get(f"/api/write/v1/pages/{page.id}/", **auth_header)
        data = response.json()
        assert data["title"] == "New Title"
        assert data["body"] == "Keep this body"


@pytest.mark.django_db
class TestDeletePage:
    def test_delete_page(self, api_client, auth_header, home_page):
        page = home_page.add_child(instance=SimplePage(title="To Delete", slug="to-delete"))
        page.save_revision()
        page_id = page.id

        response = api_client.delete(f"/api/write/v1/pages/{page_id}/", **auth_header)
        assert response.status_code == 204
        assert not Page.objects.filter(id=page_id).exists()

    def test_delete_nonexistent_returns_404(self, api_client, auth_header, home_page):
        response = api_client.delete("/api/write/v1/pages/99999/", **auth_header)
        assert response.status_code == 404
