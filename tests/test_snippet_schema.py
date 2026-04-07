import pytest


@pytest.mark.django_db
class TestSnippetSchemaDiscovery:
    def test_list_snippet_types(self, api_client, auth_header):
        response = api_client.get("/api/write/v1/schema/snippets/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        types = [t["type"] for t in data["snippet_types"]]
        assert "testapp.Category" in types
        assert "testapp.Tag" in types

    def test_snippet_type_has_fields_summary(self, api_client, auth_header):
        response = api_client.get("/api/write/v1/schema/snippets/", **auth_header)
        data = response.json()
        cat_type = next(t for t in data["snippet_types"] if t["type"] == "testapp.Category")
        assert "name" in cat_type["fields_summary"]
        assert "slug" in cat_type["fields_summary"]

    def test_get_snippet_type_schema(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/snippets/testapp.Category/", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert "create_schema" in data
        assert "patch_schema" in data
        assert "read_schema" in data
        # Verify no page-specific fields in create schema
        create_props = data["create_schema"]["properties"]
        assert "parent" not in create_props
        assert "action" not in create_props
        assert "type" in create_props

    def test_get_unknown_snippet_type(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/snippets/fake.Model/", **auth_header
        )
        assert response.status_code == 404
