import pytest
from django.test import Client, TestCase

from testapp.models import BlogIndexPage, BlogPage, SimplePage
from wagtail.models import Page, Site
from django.contrib.auth.models import User
from wagtail_write_api.models import ApiToken


class _PageTreeMixin:
    """Shared setUpTestData for read-only page tests.

    Django's setUpTestData creates data once per class and wraps each test
    in a savepoint, so the page tree is built once (~0.5 s) rather than
    once per test method.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", "admin@test.com", "pw")
        token, _ = ApiToken.objects.get_or_create(user=cls.admin)
        cls.auth = {"HTTP_AUTHORIZATION": f"Bearer {token.key}"}

        root = Page.objects.filter(depth=1).first()
        cls.home = root.add_child(title="Home", slug="home-test")
        Site.objects.update_or_create(
            is_default_site=True,
            defaults={"hostname": "localhost", "root_page": cls.home},
        )

        cls.simple = cls.home.add_child(
            instance=SimplePage(title="Simple", slug="simple", body="Hello")
        )
        cls.simple.save_revision()

        cls.blog_index = cls.home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog", intro="Blog intro")
        )
        cls.blog_index.save_revision()

        cls.blog1 = cls.blog_index.add_child(
            instance=BlogPage(title="First Post", slug="first-post", published_date="2026-01-01")
        )
        cls.blog1.save_revision()
        cls.blog1.get_latest_revision().publish()

        cls.blog2 = cls.blog_index.add_child(
            instance=BlogPage(title="Draft Post", slug="draft-post", published_date="2026-02-01")
        )
        cls.blog2.save_revision()


class TestListPages(_PageTreeMixin, TestCase):
    def test_list_returns_items(self):
        response = self.client.get("/api/write/v1/pages/", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert data["meta"]["total_count"] > 0

    def test_list_requires_auth(self):
        response = self.client.get("/api/write/v1/pages/")
        assert response.status_code == 401

    def test_filter_by_type(self):
        response = self.client.get("/api/write/v1/pages/?type=testapp.BlogPage", **self.auth)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["meta"]["type"] == "testapp.BlogPage"

    def test_filter_by_parent(self):
        parent_id = self.blog_index.id
        response = self.client.get(f"/api/write/v1/pages/?parent={parent_id}", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_filter_by_parent_path(self):
        response = self.client.get("/api/write/v1/pages/?parent=/blog/", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_filter_by_parent_invalid_returns_empty(self):
        response = self.client.get("/api/write/v1/pages/?parent=/nonexistent/", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    def test_filter_by_status_live(self):
        response = self.client.get("/api/write/v1/pages/?status=live", **self.auth)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["meta"]["live"] is True

    def test_filter_by_status_draft(self):
        response = self.client.get("/api/write/v1/pages/?status=draft", **self.auth)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["meta"]["live"] is False

    def test_pagination(self):
        response = self.client.get("/api/write/v1/pages/?offset=0&limit=1", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["meta"]["total_count"] > 1


class TestDetailPage(_PageTreeMixin, TestCase):
    def test_detail_returns_page(self):
        page_id = self.blog1.id
        response = self.client.get(f"/api/write/v1/pages/{page_id}/", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == page_id
        assert data["title"] == "First Post"

    def test_detail_includes_meta(self):
        page_id = self.blog1.id
        response = self.client.get(f"/api/write/v1/pages/{page_id}/", **self.auth)
        data = response.json()
        meta = data["meta"]
        assert "type" in meta
        assert "live" in meta
        assert "has_unpublished_changes" in meta
        assert "parent_id" in meta
        assert "user_permissions" in meta

    def test_detail_404_for_nonexistent(self):
        response = self.client.get("/api/write/v1/pages/99999/", **self.auth)
        assert response.status_code == 404

    def test_detail_includes_type_specific_fields(self):
        page_id = self.blog1.id
        response = self.client.get(f"/api/write/v1/pages/{page_id}/", **self.auth)
        data = response.json()
        assert "published_date" in data


class TestDetailPageDrafts(_PageTreeMixin, TestCase):
    """Draft-aware reads — these mutate the page tree so they get their own class."""

    def test_detail_returns_draft_content_by_default(self):
        """When a page has unpublished changes, detail returns the draft."""
        self.blog1.title = "Updated Title (draft)"
        self.blog1.save_revision()

        response = self.client.get(f"/api/write/v1/pages/{self.blog1.id}/", **self.auth)
        data = response.json()
        assert data["title"] == "Updated Title (draft)"

    def test_detail_with_version_live(self):
        """?version=live returns the published content, not the draft DB row."""
        self.blog1.refresh_from_db()
        self.blog1.title = "Updated Title (draft)"
        self.blog1.save()
        self.blog1.save_revision()

        response = self.client.get(
            f"/api/write/v1/pages/{self.blog1.id}/?version=live", **self.auth
        )
        data = response.json()
        assert data["title"] == "First Post"


class TestUrlPath(_PageTreeMixin, TestCase):
    def test_list_includes_url_path(self):
        response = self.client.get("/api/write/v1/pages/?slug=first-post", **self.auth)
        data = response.json()
        item = data["items"][0]
        assert item["meta"]["url_path"] == "/blog/first-post/"

    def test_list_root_page_url_path(self):
        """The site root page should have url_path '/'."""
        home_id = self.home.id
        response = self.client.get(f"/api/write/v1/pages/{home_id}/", **self.auth)
        data = response.json()
        assert data["meta"]["url_path"] == "/"

    def test_detail_includes_url_path(self):
        page_id = self.blog1.id
        response = self.client.get(f"/api/write/v1/pages/{page_id}/", **self.auth)
        data = response.json()
        assert data["meta"]["url_path"] == "/blog/first-post/"

    def test_detail_simple_page_url_path(self):
        page_id = self.simple.id
        response = self.client.get(f"/api/write/v1/pages/{page_id}/", **self.auth)
        data = response.json()
        assert data["meta"]["url_path"] == "/simple/"


class TestFilterBySlug(_PageTreeMixin, TestCase):
    def test_filter_by_slug(self):
        response = self.client.get("/api/write/v1/pages/?slug=first-post", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == "first-post"

    def test_filter_by_slug_no_match(self):
        response = self.client.get("/api/write/v1/pages/?slug=nonexistent-slug", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    def test_filter_by_slug_combined_with_type(self):
        response = self.client.get(
            "/api/write/v1/pages/?slug=first-post&type=testapp.BlogPage", **self.auth
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["meta"]["type"] == "testapp.BlogPage"


class TestFilterByPath(_PageTreeMixin, TestCase):
    def test_filter_by_path(self):
        response = self.client.get("/api/write/v1/pages/?path=/blog/first-post/", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == "first-post"

    def test_filter_by_path_no_trailing_slash(self):
        response = self.client.get("/api/write/v1/pages/?path=/blog/first-post", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    def test_filter_by_path_no_match(self):
        response = self.client.get("/api/write/v1/pages/?path=/nonexistent/path/", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    def test_filter_by_path_root_level(self):
        response = self.client.get("/api/write/v1/pages/?path=/simple/", **self.auth)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == "simple"
