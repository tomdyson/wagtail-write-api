# CLAUDE.md

## Project overview

wagtail-write-api is a read/write REST API plugin for Wagtail CMS, built on Django Ninja. Wagtail's built-in API is read-only; this adds full CRUD for pages and images.

## Key commands

```bash
uv run pytest                        # run tests
uv run ruff check src/ tests/        # lint
uv run ruff format src/ tests/       # format
```

Example app (for manual testing):
```bash
cd example
uv run python manage.py migrate
uv run python manage.py seed_demo    # creates users, pages, tokens
uv run python manage.py runserver
```

## Architecture

- `src/wagtail_write_api/api.py` — NinjaAPI instance, global exception handlers
- `src/wagtail_write_api/endpoints/pages.py` — Page CRUD, publish/unpublish, copy/move, revisions
- `src/wagtail_write_api/endpoints/images.py` — Image upload and CRUD
- `src/wagtail_write_api/schema/` — Dynamic Pydantic schemas generated from Wagtail models at startup
- `src/wagtail_write_api/converters/rich_text.py` — Markdown/HTML to Wagtail internal format
- `example/testapp/models.py` — Test page models used by both the example app and test suite

See [docs/development/contributing.md](docs/development/contributing.md) for full project structure.

## API docs

- [Pages API](docs/api/pages.md) — endpoints, request/response formats, error responses
- [Images API](docs/api/images.md)
- [Rich text guide](docs/guides/rich-text.md) — markdown/HTML/wagtail format input
- [StreamField guide](docs/guides/streamfield.md) — block list format
- [Permissions guide](docs/guides/permissions.md)

## Testing

Tests are in `tests/` using pytest-django. The test DB uses models from `example/testapp/models.py`.

Key conventions:
- Fixtures `api_client`, `auth_header`, `home_page` are in `tests/conftest.py`
- After calling `revision.publish()`, always `refresh_from_db()` before further modifications — otherwise `save()` clobbers `live_revision_id`
- API responses use status 422 for business logic validation errors (invalid type, bad parent, malformed field data), 400 for Django validation errors

## Documentation

The `docs/` directory contains the user-facing documentation (served via GitHub Pages). When changing API behaviour, error responses, endpoints, or request/response formats, update the corresponding docs:

- `docs/api/pages.md` — endpoint reference, error status codes, request/response examples
- `docs/api/images.md` — image endpoint reference
- `docs/api/authentication.md` — auth details
- `docs/guides/` — rich text, StreamField, permissions, workflow guides
- `docs/development/contributing.md` — project structure, test table, dev setup

## Releasing

1. Update version in `pyproject.toml` and `src/wagtail_write_api/__init__.py`
2. Commit, push to `main`
3. `gh release create v<version> --generate-notes`

CI publishes to PyPI automatically via trusted publishing.
