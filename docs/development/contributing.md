# Contributing

## Setting up the development environment

Clone the repository and install dependencies:

```bash
git clone https://github.com/tomdyson/wagtail-write-api.git
cd wagtail-write-api
uv venv && uv pip install -e ".[dev]"
```

## Running tests

```bash
uv run pytest
```

The test suite uses a Django test database with models defined in `example/testapp/models.py`. Tests are in the `tests/` directory.

### Test structure

| File | Coverage |
|------|----------|
| `test_auth.py` | Token authentication |
| `test_schema_generation.py` | Pydantic schema generation from Wagtail models |
| `test_pages_read.py` | GET list and detail endpoints |
| `test_pages_write.py` | POST, PATCH, DELETE |
| `test_pages_workflow.py` | Publish, unpublish, revisions, copy, move |
| `test_rich_text.py` | Rich text format conversion |
| `test_streamfield.py` | StreamField read/write and round-trip |
| `test_images_api.py` | Image upload, CRUD, renditions |
| `test_snippets_api.py` | Snippet CRUD (list, get, create, update, delete) |
| `test_snippet_schema.py` | Snippet schema discovery |
| `test_smoke.py` | App loads, docs endpoint reachable |

## Running the example app

The `example/` directory contains a full Wagtail project with test models:

```bash
cd example
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

This creates:

- **Users:** admin, editor, moderator, reviewer (password: `password` for all)
- **Pages:** Home, About, Blog (with 5 posts), Events (with 3 events)
- **Snippets:** 3 categories, 5 tags
- **API tokens:** printed to stdout on seed

After seeding, open:

- Wagtail admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)
- API docs: [http://localhost:8000/api/write/v1/docs](http://localhost:8000/api/write/v1/docs)

## Linting

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Project structure

```
wagtail-write-api/
├── src/wagtail_write_api/    # The package
│   ├── api.py                # NinjaAPI instance + routers
│   ├── auth.py               # Token authentication
│   ├── settings.py           # App settings with defaults
│   ├── permissions.py        # Wagtail permission enforcement
│   ├── utils.py              # Slug generation, type resolution
│   ├── schema/               # Dynamic Pydantic schema generation
│   │   ├── fields.py         # Django field → Pydantic type mapping
│   │   ├── generator.py      # Model → (Read, Create, Patch) schemas
│   │   └── registry.py       # Schema cache, auto-discovery
│   ├── endpoints/            # API endpoint handlers
│   │   ├── pages.py          # Page CRUD + workflow
│   │   ├── images.py         # Image CRUD + upload
│   │   ├── snippets.py       # Snippet CRUD
│   │   └── schema_discovery.py
│   └── converters/           # Format conversion
│       └── rich_text.py      # Markdown/HTML → Wagtail internal
├── example/                  # Demo project + test harness
│   ├── example_project/      # Django settings, urls
│   └── testapp/              # Test page models, seed command
├── tests/                    # Pytest suite
└── docs/                     # This documentation (Zensical)
```

## Design decisions

- **Django Ninja over DRF** -- Pydantic schemas give us automatic OpenAPI generation and type-safe validation
- **Dynamic schemas** -- Generated at startup from model introspection, not hand-written per model
- **Draft-first reads** -- The API is for editing, not display, so it returns the working copy by default
- **Wagtail permissions exactly** -- No shortcuts, no custom permission layer; uses `PagePermissionPolicy` directly
