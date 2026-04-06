import json
import uuid

import pytest
from django.test import Client

from testapp.models import BlogIndexPage, BlogPage


@pytest.fixture
def blog_with_streamfield(home_page):
    blog_index = home_page.add_child(
        instance=BlogIndexPage(title="Blog", slug="blog", intro="")
    )
    blog_index.save_revision().publish()

    blog = blog_index.add_child(
        instance=BlogPage(
            title="Stream Post",
            slug="stream-post",
            body=json.dumps(
                [
                    {
                        "type": "heading",
                        "value": {"text": "Hello World", "size": "h2"},
                        "id": str(uuid.uuid4()),
                    },
                    {
                        "type": "paragraph",
                        "value": "<p>Some content here</p>",
                        "id": str(uuid.uuid4()),
                    },
                ]
            ),
        )
    )
    blog.save_revision().publish()
    return blog


@pytest.mark.django_db
class TestStreamFieldRead:
    def test_streamfield_returns_list_of_blocks(self, api_client, auth_header, blog_with_streamfield):
        response = api_client.get(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/", **auth_header
        )
        data = response.json()
        assert isinstance(data["body"], list)
        assert len(data["body"]) == 2

    def test_streamfield_block_has_type_value_id(self, api_client, auth_header, blog_with_streamfield):
        response = api_client.get(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/", **auth_header
        )
        data = response.json()
        block = data["body"][0]
        assert "type" in block
        assert "value" in block
        assert "id" in block
        assert block["type"] == "heading"

    def test_struct_block_value_is_dict(self, api_client, auth_header, blog_with_streamfield):
        response = api_client.get(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/", **auth_header
        )
        data = response.json()
        heading_block = data["body"][0]
        assert isinstance(heading_block["value"], dict)
        assert heading_block["value"]["text"] == "Hello World"
        assert heading_block["value"]["size"] == "h2"


@pytest.mark.django_db
class TestStreamFieldWrite:
    def test_create_page_with_streamfield(self, api_client, auth_header, home_page):
        blog_index = home_page.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog-sf", intro="")
        )
        blog_index.save_revision().publish()

        body_data = [
            {
                "type": "heading",
                "value": {"text": "New Heading", "size": "h3"},
                "id": str(uuid.uuid4()),
            },
            {
                "type": "paragraph",
                "value": "<p>New paragraph</p>",
                "id": str(uuid.uuid4()),
            },
        ]
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.BlogPage",
                    "parent": blog_index.id,
                    "title": "SF Write Test",
                    "body": body_data,
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["body"]) == 2
        assert data["body"][0]["type"] == "heading"

    def test_round_trip_streamfield(self, api_client, auth_header, blog_with_streamfield):
        """GET -> extract body -> PATCH it back -> GET -> compare."""
        # Read
        response1 = api_client.get(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/", **auth_header
        )
        original_body = response1.json()["body"]

        # Write it back
        api_client.patch(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/",
            data=json.dumps({"body": original_body}),
            content_type="application/json",
            **auth_header,
        )

        # Read again
        response2 = api_client.get(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/", **auth_header
        )
        round_tripped_body = response2.json()["body"]

        # Compare structure (ids and values should match)
        assert len(round_tripped_body) == len(original_body)
        for orig, rt in zip(original_body, round_tripped_body):
            assert orig["type"] == rt["type"]
            assert orig["value"] == rt["value"]
