# wagtail-write-api

A read/write REST API for Wagtail CMS.

## Why?

Wagtail's built-in `wagtail.api.v2` is a **read-only** API designed for headless frontends. It exposes a curated subset of fields via `api_fields` for display purposes.

**wagtail-write-api** is a full **read/write content management API**. It:

- Introspects all editable fields on a page model
- Returns data in a format suitable for editing, not just display
- Supports the complete draft/publish workflow
- Generates OpenAPI schemas automatically via Pydantic

If you're building a mobile CMS editor, a CI/CD content pipeline, or a third-party integration that needs to both read and write Wagtail content, this plugin might help.

## Features

- **Schema discovery** -- query available page types, snippet types, and their field schemas
- **Full Page CRUD** -- create, read, update, and delete pages with proper revision tracking
- **Snippet CRUD** -- manage models registered with `@register_snippet` (categories, tags, reusable content)
- **Draft-aware reads** -- GET returns the latest draft by default, not just the published version
- **Workflow actions** -- publish, unpublish, submit for moderation, copy, move
- **StreamField support** -- read and write StreamField data with full round-trip fidelity
- **Rich text conversion** -- accept Markdown, HTML, or Wagtail's internal format
- **Image management** -- upload, list, update, and delete images with rendition URLs
- **Wagtail permissions** -- respects the same tree-based permission model as the admin
- **OpenAPI docs** -- interactive API docs at `/docs`

## Quick install

```bash
pip install wagtail-write-api
```

```python title="settings.py"
INSTALLED_APPS = [
    ...
    "wagtail_write_api",
]
```

```python title="urls.py"
urlpatterns = [
    path("api/write/v1/", include("wagtail_write_api.urls")),
    ...
]
```

The API auto-discovers your page types on startup, generates schemas, and serves interactive docs at `/api/write/v1/docs`.

## Supported versions

| | Wagtail 6.x | Wagtail 7.x |
|---|---|---|
| Python 3.10+ | Yes | Yes |
