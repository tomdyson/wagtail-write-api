"""Tests for rich text markdown round-trip fidelity.

These tests verify that content survives read (HTML→markdown) and
write (markdown→HTML) conversions without data loss.
"""

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from wagtail.models import Page, Site

from testapp.models import SimplePage
from wagtail_write_api.converters.rich_text import html_to_markdown, markdown_to_wagtail
from wagtail_write_api.models import ApiToken


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser("admin", "admin@test.com", "password")


@pytest.fixture
def admin_token(admin_user):
    token, _ = ApiToken.objects.get_or_create(user=admin_user)
    return token.key


@pytest.fixture
def auth_header(admin_token):
    return {"HTTP_AUTHORIZATION": f"Bearer {admin_token}"}


@pytest.fixture
def home_page(db):
    root = Page.objects.filter(depth=1).first()
    home = root.add_child(title="Home", slug="home-test")
    Site.objects.update_or_create(
        is_default_site=True,
        defaults={"hostname": "localhost", "root_page": home},
    )
    return home


@pytest.fixture
def simple_page(home_page):
    page = home_page.add_child(
        instance=SimplePage(
            title="Test Rich Text",
            slug="test-rich-text",
            body="<p>Hello <strong>world</strong></p>",
        )
    )
    page.save_revision().publish()
    page.refresh_from_db()
    return page


# -----------------------------------------------------------------------
# Unit tests: html_to_markdown converter
# -----------------------------------------------------------------------


class TestHtmlToMarkdown:
    def test_paragraph(self):
        assert html_to_markdown("<p>Hello world</p>") == "Hello world"

    def test_bold(self):
        result = html_to_markdown("<p>Hello <strong>world</strong></p>")
        assert "**world**" in result

    def test_italic(self):
        result = html_to_markdown("<p>Hello <em>world</em></p>")
        assert "*world*" in result

    def test_heading(self):
        result = html_to_markdown("<h2>My Heading</h2>")
        assert "## My Heading" in result

    def test_link(self):
        result = html_to_markdown('<p><a href="https://example.com">click</a></p>')
        assert "[click](https://example.com)" in result

    def test_unordered_list(self):
        result = html_to_markdown("<ul><li>One</li><li>Two</li></ul>")
        assert "One" in result
        assert "Two" in result

    def test_ordered_list(self):
        result = html_to_markdown("<ol><li>First</li><li>Second</li></ol>")
        assert "First" in result
        assert "Second" in result

    def test_multiple_paragraphs(self):
        result = html_to_markdown("<p>Paragraph one</p><p>Paragraph two</p>")
        assert "Paragraph one" in result
        assert "Paragraph two" in result

    def test_empty_string(self):
        assert html_to_markdown("") == ""

    def test_nested_formatting(self):
        result = html_to_markdown("<p>Hello <strong><em>bold italic</em></strong></p>")
        assert "bold italic" in result

    def test_image(self):
        result = html_to_markdown('<p><img src="/media/img.jpg" alt="Photo"/></p>')
        assert "![Photo](/media/img.jpg)" in result


# -----------------------------------------------------------------------
# Unit tests: round-trip markdown → HTML → markdown
# -----------------------------------------------------------------------


class TestMarkdownRoundTrip:
    """Verify that markdown→HTML→markdown preserves content."""

    def _round_trip(self, md_input):
        html = markdown_to_wagtail(md_input)
        return html_to_markdown(html)

    def test_plain_text(self):
        result = self._round_trip("Hello world")
        assert "Hello world" in result

    def test_bold(self):
        result = self._round_trip("Hello **world**")
        assert "**world**" in result

    def test_italic(self):
        result = self._round_trip("Hello *world*")
        assert "*world*" in result

    def test_heading(self):
        result = self._round_trip("## My Heading")
        assert "## My Heading" in result

    def test_link(self):
        result = self._round_trip("[click](https://example.com)")
        assert "[click](https://example.com)" in result

    def test_bullet_list(self):
        result = self._round_trip("- One\n- Two\n- Three")
        assert "One" in result
        assert "Two" in result
        assert "Three" in result

    def test_multiline(self):
        md = "# Title\n\nFirst paragraph.\n\nSecond paragraph with **bold**."
        result = self._round_trip(md)
        assert "# Title" in result
        assert "First paragraph" in result
        assert "**bold**" in result


# -----------------------------------------------------------------------
# API integration tests: ?rich_text_format=markdown
# -----------------------------------------------------------------------


class TestRichTextFormatParam:
    def test_default_returns_html(self, api_client, auth_header, simple_page):
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/", **auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert "<p>" in data["body"] or "<strong>" in data["body"]

    def test_markdown_param_returns_markdown(
        self, api_client, auth_header, simple_page
    ):
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=markdown",
            **auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        # Should not contain HTML tags
        assert "<p>" not in data["body"]
        assert "**world**" in data["body"]

    def test_unknown_format_returns_html(
        self, api_client, auth_header, simple_page
    ):
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=unknown",
            **auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        # Falls through to default HTML
        assert "<p>" in data["body"] or "Hello" in data["body"]

    def test_roundtrip_read_markdown_write_markdown(
        self, api_client, auth_header, simple_page
    ):
        """Read as markdown, write back as markdown, verify content survives."""
        # 1. Read as markdown
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=markdown",
            **auth_header,
        )
        md_body = response.json()["body"]
        assert "**world**" in md_body

        # 2. Write back as markdown
        response = api_client.patch(
            f"/api/write/v1/pages/{simple_page.id}/",
            data=json.dumps(
                {"body": {"format": "markdown", "content": md_body}}
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200

        # 3. Read again as markdown
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=markdown",
            **auth_header,
        )
        final_body = response.json()["body"]
        assert "**world**" in final_body

    def test_roundtrip_preserves_links(
        self, api_client, auth_header, simple_page
    ):
        """Write markdown with a link, verify it round-trips."""
        # Write markdown with a link
        response = api_client.patch(
            f"/api/write/v1/pages/{simple_page.id}/",
            data=json.dumps(
                {
                    "body": {
                        "format": "markdown",
                        "content": "Visit [Example](https://example.com) today",
                    }
                }
            ),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200

        # Read back as markdown
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=markdown",
            **auth_header,
        )
        body = response.json()["body"]
        assert "Example" in body
        assert "https://example.com" in body

    def test_roundtrip_preserves_headings(
        self, api_client, auth_header, simple_page
    ):
        """Write markdown with headings, verify round-trip."""
        md = "## Section One\n\nContent here.\n\n### Subsection\n\nMore content."
        response = api_client.patch(
            f"/api/write/v1/pages/{simple_page.id}/",
            data=json.dumps({"body": {"format": "markdown", "content": md}}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200

        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=markdown",
            **auth_header,
        )
        body = response.json()["body"]
        assert "## Section One" in body
        assert "### Subsection" in body
        assert "Content here" in body

    def test_roundtrip_preserves_bold_italic(
        self, api_client, auth_header, simple_page
    ):
        md = "This is **bold** and *italic* text."
        response = api_client.patch(
            f"/api/write/v1/pages/{simple_page.id}/",
            data=json.dumps({"body": {"format": "markdown", "content": md}}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200

        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=markdown",
            **auth_header,
        )
        body = response.json()["body"]
        assert "**bold**" in body
        assert "*italic*" in body

    def test_global_setting_returns_markdown(
        self, api_client, auth_header, simple_page, settings
    ):
        """RICH_TEXT_OUTPUT_FORMAT=markdown returns markdown without query param."""
        settings.WAGTAIL_WRITE_API = {"RICH_TEXT_OUTPUT_FORMAT": "markdown"}
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/", **auth_header
        )
        assert response.status_code == 200
        body = response.json()["body"]
        assert "<p>" not in body
        assert "**world**" in body

    def test_query_param_overrides_global_setting(
        self, api_client, auth_header, simple_page, settings
    ):
        """?rich_text_format=html overrides a global markdown default."""
        settings.WAGTAIL_WRITE_API = {"RICH_TEXT_OUTPUT_FORMAT": "markdown"}
        response = api_client.get(
            f"/api/write/v1/pages/{simple_page.id}/?rich_text_format=html",
            **auth_header,
        )
        assert response.status_code == 200
        body = response.json()["body"]
        assert "<p>" in body or "<strong>" in body

    def test_no_param_on_list_endpoint(
        self, api_client, auth_header, simple_page
    ):
        """List endpoint doesn't include body, so param has no effect."""
        response = api_client.get(
            "/api/write/v1/pages/?rich_text_format=markdown", **auth_header
        )
        assert response.status_code == 200
        # List items don't have body fields
        items = response.json()["items"]
        assert len(items) > 0
        assert "body" not in items[0]
