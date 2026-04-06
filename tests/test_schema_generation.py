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
