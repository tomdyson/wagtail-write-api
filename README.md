# wagtail-write-api

A read/write REST API for [Wagtail](https://wagtail.org/) CMS, built on [Django Ninja](https://django-ninja.dev/).

Wagtail's built-in API is read-only, designed for headless frontends. This plugin adds full content management: create, edit, publish, and delete pages and images via a REST API with automatic OpenAPI documentation.

**[Documentation](https://tomdyson.github.io/wagtail-write-api/)**

## Features

- **Page CRUD** with draft/publish workflow, revision history, copy, and move
- **Image management** with multipart upload and configurable renditions
- **StreamField** read/write with full round-trip fidelity
- **Rich text** input in Markdown, HTML, or Wagtail's internal format
- **Schema discovery** so clients can inspect page types and their fields
- **Wagtail permissions** enforced exactly as in the admin
- **OpenAPI docs** generated automatically from Pydantic schemas

## Quick start

```bash
pip install wagtail-write-api
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    "rest_framework",
    "rest_framework.authtoken",
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
python manage.py drf_create_token admin
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/write/v1/pages/
```

Interactive API docs are served at `/api/write/v1/docs`.

## Requirements

- Python 3.10+
- Wagtail 6.0+
- Django REST Framework (for token auth)

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

## Licence

BSD 3-Clause. See [LICENSE](LICENSE).
