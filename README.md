# wagtail-write-api

A read/write REST API for [Wagtail](https://wagtail.org/) CMS.

Wagtail's [built-in API](https://docs.wagtail.org/en/stable/advanced_topics/api/) is read-only, designed for headless frontends. This plugin adds full content management: create, edit, publish, and delete pages and images via a REST API with automatic OpenAPI documentation.

**[Documentation](https://tomdyson.github.io/wagtail-write-api/)**

## Features

- **Schema discovery** so clients can inspect page types, snippet types, and their fields
- **Page CRUD** with draft/publish workflow, revision history, copy, and move
- **Snippet CRUD** for models registered with `@register_snippet` (categories, tags, reusable content)
- **Image management** with multipart upload and configurable renditions
- **StreamField** read/write with round-trip fidelity
- **Rich text** input in Markdown, HTML, or Wagtail's internal format
- **Wagtail permissions** enforced as in the admin
- **OpenAPI docs** generated automatically from Pydantic schemas

## Quick start

```bash
pip install wagtail-write-api
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    "wagtail_write_api",
]
```

```python
# urls.py
urlpatterns = [
    path("api/write/v1/", include("wagtail_write_api.urls")),
    ...
]
```

Create a token and start using the API:

```bash
python manage.py create_api_token admin
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/write/v1/pages/
```

Interactive API docs are served at `/api/write/v1/docs`.

> **Note:** All API URLs require a trailing slash (e.g. `/pages/`, `/pages/3/`). Requests without a trailing slash will receive a `301` redirect.

## Client

**[wagapi](https://github.com/tomdyson/wagapi)** is a CLI client for this API, optimised for LLM orchestration. It translates CLI commands into HTTP calls and returns structured output:

```bash
uvx wagapi schema                                    # discover content model
uvx wagapi pages create testapp.BlogPage \
  --parent /blog/ --title "Hello" --body "..."       # create a page
uvx wagapi snippets list testapp.Category            # list snippets
```

## Requirements

- Python 3.10+
- Wagtail 6.0+

## Documentation

Full documentation is at **[tomdyson.github.io/wagtail-write-api](https://tomdyson.github.io/wagtail-write-api/)**, covering:

- [Installation](https://tomdyson.github.io/wagtail-write-api/getting-started/installation/)
- [Quickstart](https://tomdyson.github.io/wagtail-write-api/getting-started/quickstart/)
- [Configuration](https://tomdyson.github.io/wagtail-write-api/getting-started/configuration/)
- [Pages API reference](https://tomdyson.github.io/wagtail-write-api/api/pages/)
- [Images API reference](https://tomdyson.github.io/wagtail-write-api/api/images/)
- [Rich text guide](https://tomdyson.github.io/wagtail-write-api/guides/rich-text/)
- [StreamField guide](https://tomdyson.github.io/wagtail-write-api/guides/streamfield/)
- [Permissions guide](https://tomdyson.github.io/wagtail-write-api/guides/permissions/)

## Development

```bash
git clone https://github.com/tomdyson/wagtail-write-api.git
cd wagtail-write-api
uv venv && uv pip install -e ".[dev]"
uv run pytest
```

Run the example app:

```bash
cd example
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

## Releasing to PyPI

1. Update the version in `pyproject.toml` and `src/wagtail_write_api/__init__.py`
2. Commit, push to `main`
3. Create a GitHub release: `gh release create v0.2.0 --generate-notes`

The [publish workflow](.github/workflows/publish.yml) builds and uploads to PyPI automatically via trusted publishing.

## Not yet supported

The following Wagtail features are not yet covered by the API:

- **Documents** — `DocumentChooserBlock` and document uploads. Only images have API support currently.
- **Multi-site** — the API assumes a single default site. Path resolution and `url_path` may behave unexpectedly with multiple `Site` objects.
- **Locales / translations** — no support for `wagtail-localize` or Wagtail's built-in locale features. Pages are created in the default locale only.
- **TableBlock, EmbedBlock, RawHTMLBlock** — StreamField round-trip works for common block types, but these specialised blocks are untested and may not serialise correctly.
- **Scheduled publishing** — `go_live_at` / `expire_at` fields are not exposed.
- **Search promotion and redirects** — no API coverage.

Contributions welcome — see [CONTRIBUTING](docs/development/contributing.md).

## Licence

BSD 3-Clause. See [LICENSE](LICENSE).
