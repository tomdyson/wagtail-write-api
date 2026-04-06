import json

import pytest

from testapp.models import BlogIndexPage, BlogPage, SimplePage


@pytest.fixture
def draft_page(home_page):
    page = home_page.add_child(instance=SimplePage(title="Draft Page", slug="draft-wf"))
    page.save_revision()
    return page


@pytest.fixture
def live_page(home_page):
    page = home_page.add_child(instance=SimplePage(title="Live Page", slug="live-wf"))
    page.save_revision().publish()
    return page


@pytest.mark.django_db
class TestPublish:
    def test_publish_draft_page(self, api_client, auth_header, draft_page):
        response = api_client.post(f"/api/write/v1/pages/{draft_page.id}/publish/", **auth_header)
        assert response.status_code == 200
        draft_page.refresh_from_db()
        assert draft_page.live is True

    def test_publish_nonexistent_returns_404(self, api_client, auth_header, home_page):
        response = api_client.post("/api/write/v1/pages/99999/publish/", **auth_header)
        assert response.status_code == 404


@pytest.mark.django_db
class TestUnpublish:
    def test_unpublish_live_page(self, api_client, auth_header, live_page):
        response = api_client.post(f"/api/write/v1/pages/{live_page.id}/unpublish/", **auth_header)
        assert response.status_code == 200
        live_page.refresh_from_db()
        assert live_page.live is False


@pytest.mark.django_db
class TestRevisions:
    def test_list_revisions(self, api_client, auth_header, draft_page):
        # Create a couple more revisions
        draft_page.title = "Rev 2"
        draft_page.save_revision()
        draft_page.title = "Rev 3"
        draft_page.save_revision()

        response = api_client.get(f"/api/write/v1/pages/{draft_page.id}/revisions/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_get_specific_revision(self, api_client, auth_header, draft_page):
        revision = draft_page.get_latest_revision()
        response = api_client.get(
            f"/api/write/v1/pages/{draft_page.id}/revisions/{revision.id}/",
            **auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Draft Page"


@pytest.mark.django_db
class TestCopyPage:
    def test_copy_page(self, api_client, auth_header, home_page, live_page):
        response = api_client.post(
            f"/api/write/v1/pages/{live_page.id}/copy/",
            data=json.dumps({"destination": home_page.id}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Live Page"
        assert data["id"] != live_page.id


@pytest.mark.django_db
class TestMovePage:
    def test_move_page(self, api_client, auth_header, home_page):
        page = home_page.add_child(instance=SimplePage(title="Mover", slug="mover"))
        page.save_revision()
        new_parent = home_page.add_child(
            instance=SimplePage(title="New Parent", slug="new-parent")
        )
        new_parent.save_revision()

        response = api_client.post(
            f"/api/write/v1/pages/{page.id}/move/",
            data=json.dumps({"destination": new_parent.id}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200
        page.refresh_from_db()
        assert page.get_parent().id == new_parent.id
