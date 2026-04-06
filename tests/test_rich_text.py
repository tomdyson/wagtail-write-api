import json

import pytest
from django.test import Client
from wagtail.models import Page

from testapp.models import SimplePage


@pytest.mark.django_db
class TestRichTextInput:
    """Test that the RichTextInput dict format is converted to Wagtail internal."""

    def test_html_format_stores_html(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.SimplePage",
                    "parent": home_page.id,
                    "title": "Rich Text HTML",
                    "body": {"format": "html", "content": "<p>Hello <strong>world</strong></p>"},
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        # Verify stored value in DB is a string, not a dict
        page = SimplePage.objects.get(title="Rich Text HTML")
        assert isinstance(page.body, str)
        assert "<strong>world</strong>" in page.body

    def test_markdown_format_converts_to_html(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.SimplePage",
                    "parent": home_page.id,
                    "title": "Rich Text MD",
                    "body": {"format": "markdown", "content": "Hello **world**"},
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        page = SimplePage.objects.get(title="Rich Text MD")
        assert isinstance(page.body, str)
        assert "<strong>" in page.body or "<b>" in page.body

    def test_wagtail_format_passthrough(self, api_client, auth_header, home_page):
        wagtail_html = '<p>Link to <a linktype="page" id="1">home</a></p>'
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.SimplePage",
                    "parent": home_page.id,
                    "title": "Rich Text Wagtail",
                    "body": {"format": "wagtail", "content": wagtail_html},
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        page = SimplePage.objects.get(title="Rich Text Wagtail")
        assert 'linktype="page"' in page.body

    def test_plain_string_body_still_works(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.SimplePage",
                    "parent": home_page.id,
                    "title": "Plain String",
                    "body": "<p>Just plain HTML</p>",
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        page = SimplePage.objects.get(title="Plain String")
        assert page.body == "<p>Just plain HTML</p>"

    def test_markdown_wagtail_page_link(self, api_client, auth_header, home_page):
        response = api_client.post(
            "/api/write/v1/pages/",
            data=json.dumps(
                {
                    "type": "testapp.SimplePage",
                    "parent": home_page.id,
                    "title": "MD Links",
                    "body": {
                        "format": "markdown",
                        "content": f"Check [home](wagtail://page/{home_page.id}) out",
                    },
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 201
        page = SimplePage.objects.get(title="MD Links")
        assert f'id="{home_page.id}"' in page.body
        assert 'linktype="page"' in page.body
