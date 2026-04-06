import pytest
from datetime import date, datetime
from typing import Optional


@pytest.mark.django_db
class TestSchemaGeneration:
    def test_simple_page_read_schema_has_expected_fields(self):
        from wagtail_write_api.schema.registry import schema_registry

        read_schema, _, _ = schema_registry.get_schemas("testapp.SimplePage")
        fields = read_schema.model_fields
        assert "title" in fields
        assert "slug" in fields
        assert "body" in fields
        assert "id" in fields

    def test_simple_page_create_schema_has_type_and_parent(self):
        from wagtail_write_api.schema.registry import schema_registry

        _, create_schema, _ = schema_registry.get_schemas("testapp.SimplePage")
        fields = create_schema.model_fields
        assert "type" in fields
        assert "parent" in fields
        assert fields["type"].is_required()
        assert fields["parent"].is_required()

    def test_simple_page_patch_schema_all_optional(self):
        from wagtail_write_api.schema.registry import schema_registry

        _, _, patch_schema = schema_registry.get_schemas("testapp.SimplePage")
        for name, field in patch_schema.model_fields.items():
            assert not field.is_required(), f"{name} should be optional in PatchSchema"

    def test_blog_page_includes_custom_fields(self):
        from wagtail_write_api.schema.registry import schema_registry

        read_schema, _, _ = schema_registry.get_schemas("testapp.BlogPage")
        fields = read_schema.model_fields
        assert "published_date" in fields
        assert "feed_image" in fields
        assert "body" in fields

    def test_blog_page_includes_orderable_authors(self):
        from wagtail_write_api.schema.registry import schema_registry

        read_schema, _, _ = schema_registry.get_schemas("testapp.BlogPage")
        fields = read_schema.model_fields
        assert "authors" in fields

    def test_event_page_excludes_legacy_id(self):
        from wagtail_write_api.schema.registry import schema_registry

        read_schema, _, _ = schema_registry.get_schemas("testapp.EventPage")
        fields = read_schema.model_fields
        assert "legacy_id" not in fields
        assert "start_date" in fields
        assert "location" in fields

    def test_internal_fields_excluded(self):
        from wagtail_write_api.schema.registry import schema_registry

        read_schema, _, _ = schema_registry.get_schemas("testapp.SimplePage")
        fields = read_schema.model_fields
        for excluded in ["path", "depth", "numchild", "content_type", "page_ptr"]:
            assert excluded not in fields, f"{excluded} should be excluded"

    def test_field_types_correct(self):
        from wagtail_write_api.schema.registry import schema_registry

        read_schema, _, _ = schema_registry.get_schemas("testapp.EventPage")
        fields = read_schema.model_fields
        assert fields["start_date"].annotation is datetime
        assert fields["location"].annotation is str

    def test_all_page_types_registered(self):
        from wagtail_write_api.schema.registry import schema_registry

        types = schema_registry.all_page_types()
        assert "testapp.SimplePage" in types
        assert "testapp.BlogPage" in types
        assert "testapp.BlogIndexPage" in types
        assert "testapp.EventPage" in types

    def test_create_schema_parent_accepts_int_or_str(self):
        from wagtail_write_api.schema.registry import schema_registry

        _, create_schema, _ = schema_registry.get_schemas("testapp.SimplePage")
        schema = create_schema.model_json_schema()
        parent_schema = schema["properties"]["parent"]
        # Should accept both int and string (for path-based lookup)
        assert "anyOf" in parent_schema
        types = [s["type"] for s in parent_schema["anyOf"]]
        assert "integer" in types
        assert "string" in types


@pytest.mark.django_db
class TestSchemaDiscoveryEndpoint:
    def test_streamfield_blocks_in_schema(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/page-types/testapp.BlogPage/", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert "streamfield_blocks" in data
        assert "body" in data["streamfield_blocks"]
        block_types = data["streamfield_blocks"]["body"]
        type_names = [bt["type"] for bt in block_types]
        assert "heading" in type_names
        assert "paragraph" in type_names
        assert "image" in type_names
        assert "gallery" in type_names
        assert "related_pages" in type_names

    def test_structblock_has_properties(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/page-types/testapp.BlogPage/", **auth_header
        )
        data = response.json()
        heading_block = next(
            bt for bt in data["streamfield_blocks"]["body"] if bt["type"] == "heading"
        )
        schema = heading_block["schema"]
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "size" in schema["properties"]
        # ChoiceBlock should have enum
        size_schema = schema["properties"]["size"]
        assert "enum" in size_schema
        assert "h2" in size_schema["enum"]

    def test_listblock_has_items(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/page-types/testapp.BlogPage/", **auth_header
        )
        data = response.json()
        gallery_block = next(
            bt for bt in data["streamfield_blocks"]["body"] if bt["type"] == "gallery"
        )
        schema = gallery_block["schema"]
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "object"
        assert "image" in schema["items"]["properties"]
        assert "caption" in schema["items"]["properties"]

    def test_richtext_block_type(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/page-types/testapp.BlogPage/", **auth_header
        )
        data = response.json()
        para_block = next(
            bt for bt in data["streamfield_blocks"]["body"] if bt["type"] == "paragraph"
        )
        assert para_block["schema"]["type"] == "richtext"

    def test_image_chooser_block_type(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/page-types/testapp.BlogPage/", **auth_header
        )
        data = response.json()
        img_block = next(bt for bt in data["streamfield_blocks"]["body"] if bt["type"] == "image")
        assert img_block["schema"]["type"] == "image_chooser"

    def test_no_streamfields_returns_empty(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/page-types/testapp.SimplePage/", **auth_header
        )
        data = response.json()
        assert data["streamfield_blocks"] == {}

    def test_event_page_streamfield_blocks(self, api_client, auth_header):
        response = api_client.get(
            "/api/write/v1/schema/page-types/testapp.EventPage/", **auth_header
        )
        data = response.json()
        block_types = data["streamfield_blocks"]["body"]
        type_names = [bt["type"] for bt in block_types]
        assert "text" in type_names
        assert "map_embed" in type_names
        # text is RichTextBlock
        text_block = next(bt for bt in block_types if bt["type"] == "text")
        assert text_block["schema"]["type"] == "richtext"
        # map_embed is URLBlock
        url_block = next(bt for bt in block_types if bt["type"] == "map_embed")
        assert url_block["schema"]["type"] == "url"
