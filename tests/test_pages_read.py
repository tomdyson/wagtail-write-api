import json

import pytest
from django.test import Client

from testapp.models import BlogIndexPage, BlogPage, EventPage, SimplePage


@pytest.fixture
def page_tree(home_page):
    """Create a realistic page tree for testing."""
    simple = home_page.add_child(instance=SimplePage(title="Simple", slug="simple", body="Hello"))
    simple.save_revision()

    blog_index = home_page.add_child(
        instance=BlogIndexPage(title="Blog", slug="blog", intro="Blog intro")
    )
    blog_index.save_revision()

    blog1 = blog_index.add_child(
        instance=BlogPage(title="First Post", slug="first-post", published_date="2026-01-01")
    )
    blog1.save_revision()
    blog1.get_latest_revision().publish()

    blog2 = blog_index.add_child(
        instance=BlogPage(title="Draft Post", slug="draft-post", published_date="2026-02-01")
    )
    blog2.save_revision()
    # blog2 is a draft — not published

    return {
        "home": home_page,
        "simple": simple,
        "blog_index": blog_index,
        "blog1": blog1,
        "blog2": blog2,
    }


@pytest.mark.django_db
class TestListPages:
    def test_list_returns_items(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert data["meta"]["total_count"] > 0

    def test_list_requires_auth(self, api_client, page_tree):
        response = api_client.get("/api/write/v1/pages/")
        assert response.status_code == 401

    def test_filter_by_type(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?type=testapp.BlogPage", **auth_header)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["meta"]["type"] == "testapp.BlogPage"

    def test_filter_by_parent(self, api_client, auth_header, page_tree):
        parent_id = page_tree["blog_index"].id
        response = api_client.get(f"/api/write/v1/pages/?parent={parent_id}", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2  # blog1 and blog2

    def test_filter_by_status_live(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?status=live", **auth_header)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["meta"]["live"] is True

    def test_filter_by_status_draft(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?status=draft", **auth_header)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["meta"]["live"] is False

    def test_pagination(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?offset=0&limit=1", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["meta"]["total_count"] > 1


@pytest.mark.django_db
class TestDetailPage:
    def test_detail_returns_page(self, api_client, auth_header, page_tree):
        page_id = page_tree["blog1"].id
        response = api_client.get(f"/api/write/v1/pages/{page_id}/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == page_id
        assert data["title"] == "First Post"

    def test_detail_includes_meta(self, api_client, auth_header, page_tree):
        page_id = page_tree["blog1"].id
        response = api_client.get(f"/api/write/v1/pages/{page_id}/", **auth_header)
        data = response.json()
        meta = data["meta"]
        assert "type" in meta
        assert "live" in meta
        assert "has_unpublished_changes" in meta
        assert "parent_id" in meta
        assert "user_permissions" in meta

    def test_detail_returns_draft_content_by_default(self, api_client, auth_header, page_tree):
        """When a page has unpublished changes, detail returns the draft."""
        blog1 = page_tree["blog1"]
        blog1.title = "Updated Title (draft)"
        blog1.save_revision()
        # Don't publish — so there are unpublished changes

        response = api_client.get(f"/api/write/v1/pages/{blog1.id}/", **auth_header)
        data = response.json()
        assert data["title"] == "Updated Title (draft)"

    def test_detail_with_version_live(self, api_client, auth_header, page_tree):
        """?version=live returns the published content, not the draft DB row."""
        blog1 = page_tree["blog1"]
        blog1.refresh_from_db()  # pick up live_revision_id set by publish()
        blog1.title = "Updated Title (draft)"
        blog1.save()  # updates the DB row (as PATCH does)
        blog1.save_revision()
        # Don't publish — so live revision still has "First Post"

        response = api_client.get(f"/api/write/v1/pages/{blog1.id}/?version=live", **auth_header)
        data = response.json()
        assert data["title"] == "First Post"

    def test_detail_404_for_nonexistent(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/99999/", **auth_header)
        assert response.status_code == 404

    def test_detail_includes_type_specific_fields(self, api_client, auth_header, page_tree):
        page_id = page_tree["blog1"].id
        response = api_client.get(f"/api/write/v1/pages/{page_id}/", **auth_header)
        data = response.json()
        assert "published_date" in data


@pytest.mark.django_db
class TestFilterBySlug:
    def test_filter_by_slug(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?slug=first-post", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == "first-post"

    def test_filter_by_slug_no_match(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?slug=nonexistent-slug", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    def test_filter_by_slug_combined_with_type(self, api_client, auth_header, page_tree):
        response = api_client.get(
            "/api/write/v1/pages/?slug=first-post&type=testapp.BlogPage", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["meta"]["type"] == "testapp.BlogPage"


@pytest.mark.django_db
class TestFilterByPath:
    def test_filter_by_path(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?path=/blog/first-post/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == "first-post"

    def test_filter_by_path_no_trailing_slash(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?path=/blog/first-post", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    def test_filter_by_path_no_match(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?path=/nonexistent/path/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    def test_filter_by_path_root_level(self, api_client, auth_header, page_tree):
        response = api_client.get("/api/write/v1/pages/?path=/simple/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == "simple"
