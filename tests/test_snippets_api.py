import json

import pytest


@pytest.mark.django_db
class TestListSnippets:
    def test_list_requires_type(self, api_client, auth_header):
        response = api_client.get("/api/write/v1/snippets/", **auth_header)
        assert response.status_code == 422

    def test_list_unknown_type(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/snippets/?type=fake.Model", **auth_header
        )
        assert response.status_code == 422

    def test_list_categories(self, api_client, auth_header):
        from testapp.models import Category

        Category.objects.create(name="Tech", slug="tech")
        Category.objects.create(name="Science", slug="science")

        response = api_client.get(
            "/api/write/v1/snippets/?type=testapp.Category", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_count"] == 2
        assert len(data["items"]) == 2

    def test_list_search(self, api_client, auth_header):
        from testapp.models import Category

        Category.objects.create(name="Tech", slug="tech")
        Category.objects.create(name="Science", slug="science")

        response = api_client.get(
            "/api/write/v1/snippets/?type=testapp.Category&search=tech", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_count"] == 1
        assert data["items"][0]["name"] == "Tech"

    def test_list_pagination(self, api_client, auth_header):
        from testapp.models import Tag

        for i in range(5):
            Tag.objects.create(name=f"tag-{i}")

        response = api_client.get(
            "/api/write/v1/snippets/?type=testapp.Tag&limit=2&offset=0", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["meta"]["total_count"] == 5


@pytest.mark.django_db
class TestGetSnippet:
    def test_get_category(self, api_client, auth_header):
        from testapp.models import Category

        cat = Category.objects.create(name="Tech", slug="tech")

        response = api_client.get(
            f"/api/write/v1/snippets/{cat.id}/?type=testapp.Category", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Tech"
        assert data["slug"] == "tech"
        assert data["id"] == cat.id

    def test_get_not_found(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/snippets/9999/?type=testapp.Category", **auth_header
        )
        assert response.status_code == 404

    def test_get_unknown_type(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/snippets/1/?type=fake.Model", **auth_header
        )
        assert response.status_code == 422


@pytest.mark.django_db
class TestCreateSnippet:
    def test_create_category(self, api_client, auth_header):
        response = api_client.post(
            "/api/write/v1/snippets/",
            data=json.dumps(
                {"type": "testapp.Category", "name": "Arts", "slug": "arts"}
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Arts"
        assert data["slug"] == "arts"
        assert "id" in data

    def test_create_tag(self, api_client, auth_header):
        response = api_client.post(
            "/api/write/v1/snippets/",
            data=json.dumps({"type": "testapp.Tag", "name": "python"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "python"

    def test_create_missing_type(self, api_client, auth_header):
        response = api_client.post(
            "/api/write/v1/snippets/",
            data=json.dumps({"name": "Arts"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 422

    def test_create_unknown_type(self, api_client, auth_header):
        response = api_client.post(
            "/api/write/v1/snippets/",
            data=json.dumps({"type": "fake.Model", "name": "x"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 422

    def test_create_duplicate_slug(self, api_client, auth_header):
        from testapp.models import Category

        Category.objects.create(name="Tech", slug="tech")

        response = api_client.post(
            "/api/write/v1/snippets/",
            data=json.dumps(
                {"type": "testapp.Category", "name": "Tech2", "slug": "tech"}
            ),
            content_type="application/json",
            **auth_header,
        )
        # full_clean() catches unique constraint → Django ValidationError → 400
        assert response.status_code == 400


@pytest.mark.django_db
class TestUpdateSnippet:
    def test_update_category(self, api_client, auth_header):
        from testapp.models import Category

        cat = Category.objects.create(name="Tech", slug="tech")

        response = api_client.patch(
            f"/api/write/v1/snippets/{cat.id}/?type=testapp.Category",
            data=json.dumps({"name": "Technology"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Technology"
        assert data["slug"] == "tech"  # unchanged

    def test_update_not_found(self, api_client, auth_header):
        response = api_client.patch(
            "/api/write/v1/snippets/9999/?type=testapp.Category",
            data=json.dumps({"name": "x"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteSnippet:
    def test_delete_category(self, api_client, auth_header):
        from testapp.models import Category

        cat = Category.objects.create(name="Tech", slug="tech")

        response = api_client.delete(
            f"/api/write/v1/snippets/{cat.id}/?type=testapp.Category",
            **auth_header,
        )
        assert response.status_code == 204
        assert not Category.objects.filter(id=cat.id).exists()

    def test_delete_not_found(self, api_client, auth_header):
        response = api_client.delete(
            "/api/write/v1/snippets/9999/?type=testapp.Category",
            **auth_header,
        )
        assert response.status_code == 404
