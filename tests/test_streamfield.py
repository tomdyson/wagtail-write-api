import json
import uuid

import pytest
from django.contrib.auth.models import User
from django.test import TestCase

from testapp.models import BlogIndexPage, BlogPage
from wagtail.models import Page, Site
from wagtail_write_api.models import ApiToken


class TestStreamFieldRead(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin_sf", "sf@test.com", "pw")
        token, _ = ApiToken.objects.get_or_create(user=cls.admin)
        cls.auth = {"HTTP_AUTHORIZATION": f"Bearer {token.key}"}

        root = Page.objects.filter(depth=1).first()
        home = root.add_child(title="Home", slug="home-sf")
        Site.objects.update_or_create(
            is_default_site=True,
            defaults={"hostname": "localhost", "root_page": home},
        )
        blog_index = home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog", intro="")
        )
        blog_index.save_revision().publish()

        # Create a second page to reference in related_pages
        cls.other_page = blog_index.add_child(
            instance=BlogPage(
                title="Other Post",
                slug="other-post",
                body=json.dumps([]),
            )
        )
        cls.other_page.save_revision().publish()

        cls.blog = blog_index.add_child(
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
                        {
                            "type": "related_pages",
                            "value": [cls.other_page.id],
                            "id": str(uuid.uuid4()),
                        },
                    ]
                ),
            )
        )
        cls.blog.save_revision().publish()

    def test_streamfield_returns_list_of_blocks(self):
        response = self.client.get(f"/api/write/v1/pages/{self.blog.id}/", **self.auth)
        data = response.json()
        assert isinstance(data["body"], list)
        assert len(data["body"]) == 3

    def test_streamfield_block_has_type_value_id(self):
        response = self.client.get(f"/api/write/v1/pages/{self.blog.id}/", **self.auth)
        data = response.json()
        block = data["body"][0]
        assert "type" in block
        assert "value" in block
        assert "id" in block
        assert block["type"] == "heading"

    def test_list_block_value_is_list(self):
        """ListBlock values (e.g. related_pages) must serialize as JSON arrays, not string reprs."""
        response = self.client.get(f"/api/write/v1/pages/{self.blog.id}/", **self.auth)
        data = response.json()
        related = next(b for b in data["body"] if b["type"] == "related_pages")
        assert isinstance(related["value"], list), f"Expected list, got {type(related['value'])}: {related['value']}"
        assert related["value"] == [self.other_page.id]

    def test_struct_block_value_is_dict(self):
        response = self.client.get(f"/api/write/v1/pages/{self.blog.id}/", **self.auth)
        data = response.json()
        heading_block = data["body"][0]
        assert isinstance(heading_block["value"], dict)
        assert heading_block["value"]["text"] == "Hello World"
        assert heading_block["value"]["size"] == "h2"


@pytest.fixture
def blog_with_streamfield(home_page):
    blog_index = home_page.add_child(instance=BlogIndexPage(title="Blog", slug="blog", intro=""))
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

    def test_write_paragraph_with_markdown_format(
        self, api_client, auth_header, blog_with_streamfield
    ):
        """RichTextBlock values accept {format: 'markdown', content: '...'} like RichTextField."""
        body_data = [
            {
                "type": "heading",
                "value": {"text": "Keep This", "size": "h2"},
                "id": str(uuid.uuid4()),
            },
            {
                "type": "paragraph",
                "value": {"format": "markdown", "content": "Hello **world**"},
                "id": str(uuid.uuid4()),
            },
        ]
        response = api_client.patch(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/",
            data=json.dumps({"body": body_data}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        # Paragraph should be stored as HTML
        para = data["body"][1]
        assert para["type"] == "paragraph"
        assert "<strong>world</strong>" in para["value"]
        assert "format" not in str(para["value"])

    def test_markdown_round_trip_streamfield(
        self, api_client, auth_header, blog_with_streamfield
    ):
        """GET with ?rich_text_format=markdown, PATCH back with markdown wrapper."""
        # Read as markdown
        response1 = api_client.get(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/?rich_text_format=markdown",
            **auth_header,
        )
        body = response1.json()["body"]

        # Wrap paragraph values in markdown format dict for write
        patched_body = []
        for block in body:
            if block["type"] == "paragraph" and isinstance(block["value"], str):
                patched_body.append(
                    {**block, "value": {"format": "markdown", "content": block["value"]}}
                )
            else:
                patched_body.append(block)

        # Write back
        response2 = api_client.patch(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/",
            data=json.dumps({"body": patched_body}),
            content_type="application/json",
            **auth_header,
        )
        assert response2.status_code == 200

        # Read again (HTML) and verify content survived
        response3 = api_client.get(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/", **auth_header
        )
        final_body = response3.json()["body"]
        para = next(b for b in final_body if b["type"] == "paragraph")
        assert "content" in para["value"] or "<p>" in para["value"]

    def test_plain_string_paragraph_still_works(
        self, api_client, auth_header, blog_with_streamfield
    ):
        """Plain HTML strings for RichTextBlock values continue to work."""
        body_data = [
            {
                "type": "paragraph",
                "value": "<p>Plain HTML</p>",
                "id": str(uuid.uuid4()),
            },
        ]
        response = api_client.patch(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/",
            data=json.dumps({"body": body_data}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200
        para = response.json()["body"][0]
        assert para["value"] == "<p>Plain HTML</p>"

    def test_list_block_round_trip(self, api_client, auth_header, blog_with_streamfield):
        """Write a ListBlock (related_pages), read it back, verify it round-trips."""
        target_id = blog_with_streamfield.id
        body_data = [
            {
                "type": "related_pages",
                "value": [target_id],
                "id": str(uuid.uuid4()),
            },
        ]
        response = api_client.patch(
            f"/api/write/v1/pages/{blog_with_streamfield.id}/",
            data=json.dumps({"body": body_data}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        related = data["body"][0]
        assert related["type"] == "related_pages"
        assert isinstance(related["value"], list)
        assert related["value"] == [target_id]
