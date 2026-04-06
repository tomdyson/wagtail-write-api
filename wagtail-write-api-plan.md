# wagtail-content-api — Comprehensive Implementation Plan

## Project Summary

**wagtail-content-api** is an open-source Wagtail plugin that provides a read/write REST API for managing Wagtail content programmatically — targeting use cases like native mobile CMS editors, CI/CD content pipelines, and third-party integrations. It is built on Django Ninja (Pydantic + OpenAPI 3.x) and is designed to be installable with minimal configuration.

**Key distinction from Wagtail's built-in API:** The existing `wagtail.api.v2` is a read-only API designed for headless frontend consumption, exposing a curated subset of fields via `api_fields`. This plugin is a full **read/write content management API** — it introspects *all* editable fields on a page model, returns them in a format suitable for editing (not just display), supports the complete draft/publish workflow, and provides automatically-generated OpenAPI schemas. A mobile CMS editor needs to both read the current editable state of a page and write changes back — this plugin serves both sides of that round-trip, unlike the built-in API which only serves the read/display side.

---

## Design Decisions (Confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Django Ninja | Pydantic schemas → automatic OpenAPI 3.x; simpler than DRF for schema generation |
| Scope (v1) | Pages + Images | Documents and Snippets deferred to v2 |
| Wagtail support | 6.0+ only | Avoids pre-6.0 permission API differences; cleaner codebase with fewer compat shims |
| Workflow | Full (draft, publish, unpublish, submit for moderation) | Required for real CMS editing use cases |
| Rich text input | Wagtail internal format, standard HTML, AND Markdown | Markdown is natural for mobile; conversion layer handles all three |
| Field discovery | Introspect all model fields, with `write_api_exclude` opt-out | Separate concern from `api_fields` (which serves headless read) |
| Auth | DRF TokenAuthentication (via Django Ninja's `HttpBearer`) | Simple, well-understood; JWT can be added later |
| Schema generation | Dynamic Pydantic schemas from page model introspection | Using `ninja.orm.create_schema` as foundation, with custom extensions for StreamField |
| Package name | `wagtail-content-api` | PyPI: `wagtail-content-api`, import: `wagtail_content_api` |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Django Ninja API                     │
│              /api/content/v1/                         │
├──────────┬──────────┬───────────┬───────────────────┤
│  Schema  │  Pages   │  Images   │  Auth / Tokens    │
│ Discovery│  CRUD +  │  Upload + │  (HttpBearer +    │
│ Endpoint │ Workflow │  CRUD     │  DRF Token)       │
├──────────┴──────────┴───────────┴───────────────────┤
│              Schema Generation Layer                  │
│  (Model introspection → Pydantic schemas at startup)  │
├─────────────────────────────────────────────────────┤
│              Rich Text Conversion Layer               │
│  (Markdown ↔ HTML ↔ Wagtail internal format)         │
├─────────────────────────────────────────────────────┤
│              Permission Enforcement Layer             │
│  (Wagtail PagePermissionPolicy + tree permissions)   │
├─────────────────────────────────────────────────────┤
│              Wagtail Core                             │
│  (Page models, StreamField, Revisions, Workflows)    │
└─────────────────────────────────────────────────────┘
```

---

## Package Structure

```
wagtail-content-api/
├── pyproject.toml
├── README.md
├── LICENSE                        # BSD-3 (matches Wagtail)
├── CHANGELOG.md
├── Makefile                       # top-level: `make test`, `make lint`
│
├── src/
│   └── wagtail_content_api/
│       ├── __init__.py
│       ├── apps.py                # Django AppConfig
│       ├── api.py                 # NinjaAPI instance + router assembly
│       ├── urls.py                # URL conf (single include)
│       ├── auth.py                # Token auth implementation
│       ├── settings.py            # App settings with defaults
│       ├── schema/
│       │   ├── __init__.py
│       │   ├── generator.py       # Core: model → Pydantic schema
│       │   ├── registry.py        # Schema registry (caches generated schemas)
│       │   ├── fields.py          # Field type mappings (Django/Wagtail → Pydantic)
│       │   ├── streamfield.py     # StreamField → nested Pydantic schemas
│       │   └── rich_text.py       # RichText field schema + format negotiation
│       ├── endpoints/
│       │   ├── __init__.py
│       │   ├── pages.py           # Page CRUD + workflow actions
│       │   ├── images.py          # Image upload + CRUD
│       │   └── schema_discovery.py # GET /schema/pages/{type}
│       ├── converters/
│       │   ├── __init__.py
│       │   ├── rich_text.py       # Markdown ↔ HTML ↔ Wagtail internal
│       │   └── streamfield.py     # StreamField JSON ↔ API representation
│       ├── permissions.py         # Wagtail permission checks for API
│       └── utils.py               # Page tree helpers, slug generation, etc.
│
├── example/                       # Demo project — also the test harness
│   ├── manage.py
│   ├── Makefile                   # `make run`, `make seed`, `make test`
│   ├── README.md                  # How to run the demo
│   ├── example_project/
│   │   ├── settings.py            # Minimal Wagtail settings (SQLite, DEBUG=True)
│   │   ├── urls.py                # Includes wagtail_content_api + wagtail admin
│   │   └── wsgi.py
│   └── testapp/                   # Shared by demo AND tests
│       ├── __init__.py
│       ├── models.py              # Deliberately complex page models (see below)
│       ├── factories.py           # factory_boy factories for test data
│       ├── wagtail_hooks.py       # Any hook registrations for testing
│       └── management/
│           └── commands/
│               └── seed_demo.py   # Creates a realistic page tree + users
│
└── tests/                         # Pytest suite — imports from example/testapp/
    ├── conftest.py                # Django settings, fixtures, API client helpers
    ├── test_schema_generation.py
    ├── test_pages_read.py         # GET list, detail, draft vs live, filtering
    ├── test_pages_write.py        # POST create, PATCH update, DELETE
    ├── test_pages_workflow.py     # Publish, unpublish, submit for moderation
    ├── test_pages_tree.py         # Move, copy, parent/child constraints
    ├── test_images_api.py
    ├── test_rich_text.py          # All conversion paths, edge cases
    ├── test_streamfield.py        # Nested blocks, round-trip fidelity
    ├── test_permissions.py        # Tree-based, per-type, owner-based
    └── test_auth.py               # Token auth, invalid tokens, inactive users
```

### Example App Models (`example/testapp/models.py`)

The test models are designed to exercise every hard case the schema generator will face:

```python
# Simplified sketch — the real models would be fully fleshed out

class SimplePage(Page):
    """Minimal page — just title + body. Sanity check baseline."""
    body = RichTextField(blank=True)
    content_panels = Page.content_panels + [FieldPanel('body')]

class BlogIndexPage(Page):
    """Parent-only page. Tests subpage_types constraint."""
    intro = RichTextField(blank=True)
    subpage_types = ['testapp.BlogPage']

class BlogPage(Page):
    """The kitchen sink. Tests most field types + StreamField + Orderables."""
    published_date = models.DateField(null=True, blank=True)
    feed_image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, ...)
    body = StreamField([
        ('heading', blocks.StructBlock([
            ('text', blocks.CharBlock()),
            ('size', blocks.ChoiceBlock(choices=[('h2','H2'), ('h3','H3'), ('h4','H4')])),
        ])),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('gallery', blocks.ListBlock(blocks.StructBlock([   # nested list of structs
            ('image', ImageChooserBlock()),
            ('caption', blocks.CharBlock(required=False)),
        ]))),
        ('related_pages', blocks.ListBlock(PageChooserBlock())),  # list of page refs
    ], use_json_field=True)

    parent_page_types = ['testapp.BlogIndexPage']
    subpage_types = []

class BlogPageAuthor(Orderable):
    """Tests InlinePanel / Orderable child handling."""
    page = ParentalKey(BlogPage, related_name='authors')
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=100, blank=True)

class EventPage(Page):
    """Tests date ranges, simple fields, and a different StreamField config."""
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255)
    body = StreamField([
        ('text', blocks.RichTextBlock()),
        ('map_embed', blocks.URLBlock()),
    ], use_json_field=True)

    # Example of write_api_exclude
    write_api_exclude = ['legacy_id']
    legacy_id = models.CharField(max_length=50, blank=True)
```

### Seed Command (`seed_demo.py`)

The seed command creates a usable demo environment in one step:

```
cd example && python manage.py seed_demo
```

It creates:
- **Users:** An admin (superuser), an editor (add/edit permissions), a moderator (add/edit/publish), and a read-only reviewer
- **Page tree:** Root → Home → BlogIndex → 5 BlogPages (with StreamField content, authors, images) + EventsIndex → 3 EventPages
- **Images:** A handful of sample images (can use placeholder PNGs generated in code)
- **API tokens:** Pre-generated DRF tokens for each user, printed to stdout so developers can copy-paste into curl/Postman

After seeding, `make run` starts the dev server and you can:
- Browse the Wagtail admin at `/admin/`
- Hit the interactive API docs at `/api/content/v1/docs`
- Test with curl using the printed tokens

---

## Detailed Component Specifications

### 1. Installation & Configuration

**Goal: 3 lines to get running.**

```python
# settings.py
INSTALLED_APPS = [
    ...
    'wagtail_content_api',
]

# urls.py
from wagtail_content_api.urls import api_urls
urlpatterns = [
    path('api/content/v1/', include(api_urls)),
    ...
]
```

That's it. The app auto-discovers page types on startup, generates schemas, and serves the OpenAPI docs at `/api/content/v1/docs`.

**Optional settings (all have sensible defaults):**

```python
WAGTAIL_CONTENT_API = {
    # Rich text: which format to return in GET responses
    # Options: "wagtail" (internal), "html" (expanded), "markdown"
    "RICH_TEXT_OUTPUT_FORMAT": "html",

    # Page types to exclude from the API entirely
    "EXCLUDE_PAGE_TYPES": [],  # e.g. ["myapp.InternalPage"]

    # Base path for OpenAPI docs
    "DOCS_URL": "/docs",

    # Whether to require auth for read operations (default: True)
    "REQUIRE_AUTH_FOR_READ": True,

    # Pagination
    "DEFAULT_PAGE_SIZE": 20,
    "MAX_PAGE_SIZE": 100,
}
```

### 2. Schema Generation Layer (`schema/`)

This is the hardest and most important part of the project. The schema generator introspects Wagtail page models at startup and produces Pydantic schemas dynamically.

#### 2a. Model Introspection (`generator.py`)

```python
# Pseudocode for the core algorithm:

def generate_schemas_for_model(model_class):
    """
    Introspect a Wagtail Page subclass and produce:
    - ReadSchema  (for GET responses)
    - CreateSchema (for POST)
    - PatchSchema  (for PATCH, all fields optional)
    """
    fields = {}

    # 1. Walk Django model fields (skip internal Wagtail/treebeard fields)
    SKIP_FIELDS = {
        'id', 'page_ptr', 'content_type', 'path', 'depth', 'numchild',
        'url_path', 'translation_key', 'locale', 'draft_title',
        'live_revision', 'latest_revision', 'page_ptr_id',
    }

    for field in model_class._meta.get_fields():
        if field.name in SKIP_FIELDS:
            continue
        if field.name in getattr(model_class, 'write_api_exclude', []):
            continue
        pydantic_field = map_django_field(field)
        if pydantic_field:
            fields[field.name] = pydantic_field

    # 2. Handle StreamField specially
    for field_name, field in get_streamfield_fields(model_class):
        fields[field_name] = generate_streamfield_schema(field)

    # 3. Handle inline/child models (Orderables)
    for rel in model_class._meta.related_objects:
        if issubclass(rel.related_model, Orderable):
            fields[rel.name] = List[generate_orderable_schema(rel.related_model)]

    # 4. Build the three schema variants
    ReadSchema = create_model(f'{model_class.__name__}Read', **fields, ...)
    CreateSchema = create_model(f'{model_class.__name__}Create', ...)  # minus read-only
    PatchSchema = create_model(f'{model_class.__name__}Patch', ...)    # all optional

    return ReadSchema, CreateSchema, PatchSchema
```

#### 2b. Field Type Mapping (`fields.py`)

| Django/Wagtail Field | Pydantic Type | Notes |
|----------------------|---------------|-------|
| `CharField`, `TextField` | `str` | |
| `IntegerField` | `int` | |
| `FloatField` | `float` | |
| `BooleanField` | `bool` | |
| `DateField` | `date` | |
| `DateTimeField` | `datetime` | |
| `URLField` | `HttpUrl` | Pydantic URL validation |
| `EmailField` | `EmailStr` | Pydantic email validation |
| `ForeignKey` (to Page) | `int \| None` | Page ID reference |
| `ForeignKey` (to Image) | `int \| None` | Image ID reference |
| `RichTextField` | `RichTextInput` | Custom type with format field |
| `StreamField` | `list[StreamBlockUnion]` | Discriminated union of block schemas |
| `TaggableManager` | `list[str]` | |
| Orderable children | `list[ChildSchema]` | Nested schema |

#### 2c. StreamField Schema Generation (`streamfield.py`)

This is where complexity lives. StreamField definitions are recursive block trees. The generator must walk them and produce corresponding Pydantic models.

```python
def generate_streamfield_schema(stream_field):
    """
    Given a StreamField definition, produce a Pydantic schema
    that validates the JSON structure for write operations.
    """
    block_schemas = {}

    for name, block in stream_field.stream_block.child_blocks.items():
        if isinstance(block, CharBlock):
            block_schemas[name] = str
        elif isinstance(block, RichTextBlock):
            block_schemas[name] = RichTextInput
        elif isinstance(block, IntegerBlock):
            block_schemas[name] = int
        elif isinstance(block, ImageChooserBlock):
            block_schemas[name] = int  # image ID
        elif isinstance(block, PageChooserBlock):
            block_schemas[name] = int  # page ID
        elif isinstance(block, StructBlock):
            # Recurse: generate a nested Pydantic model
            block_schemas[name] = generate_struct_schema(block)
        elif isinstance(block, ListBlock):
            inner = generate_block_schema(block.child_block)
            block_schemas[name] = list[inner]
        elif isinstance(block, StreamBlock):
            # Nested StreamBlock — recurse
            block_schemas[name] = generate_streamfield_schema_inner(block)

    # Produce a discriminated union:
    # Each block becomes { "type": "block_name", "value": <BlockSchema>, "id": "uuid" }
    return list[StreamBlockItem]  # where StreamBlockItem is a tagged union
```

**API representation of StreamField (matching Wagtail's DB format with additions):**

```json
{
  "body": [
    {
      "type": "heading",
      "value": {"text": "Hello world", "size": "h2"},
      "id": "a1b2c3d4"
    },
    {
      "type": "paragraph",
      "value": "<p>Some content with <a linktype=\"page\" id=\"5\">a link</a></p>",
      "id": "e5f6g7h8"
    },
    {
      "type": "image",
      "value": 42,
      "id": "i9j0k1l2"
    }
  ]
}
```

**Key design choice:** The StreamField JSON format matches Wagtail's internal storage format. This avoids lossy conversion and means the API can be used for full round-trip editing. The `id` field on each block is the UUID Wagtail uses for block identity — clients must preserve it on updates and generate new UUIDs for new blocks.

#### 2d. Rich Text Schema (`rich_text.py`)

Rich text fields accept input in three formats, indicated by a wrapper object:

```python
class RichTextInput(Schema):
    format: Literal["wagtail", "html", "markdown"] = "html"
    content: str
```

**Example POST body:**

```json
{
  "body": {
    "format": "markdown",
    "content": "# Hello\n\nA paragraph with [a link](/about/)."
  }
}
```

Or for Wagtail's internal format:

```json
{
  "body": {
    "format": "wagtail",
    "content": "<p>Text with <a linktype=\"page\" id=\"5\">a link</a></p>"
  }
}
```

**GET responses** return rich text in whichever format is configured via `RICH_TEXT_OUTPUT_FORMAT`, defaulting to expanded HTML.

### 3. Rich Text Conversion Layer (`converters/rich_text.py`)

Three conversion paths:

```
Markdown  ──→  HTML  ──→  Wagtail internal format
         ←──       ←──
```

**Markdown → HTML:** Use the `markdown` Python library with a custom extension that handles Wagtail link syntax. For inbound markdown, standard links are converted to plain `<a href>` tags. If the client wants to reference internal Wagtail pages, they use a custom syntax:

```markdown
Check out [our about page](wagtail://page/5) for more info.
A [document link](wagtail://document/12) is also possible.
```

This is converted to `<a linktype="page" id="5">our about page</a>` in Wagtail's storage format.

**HTML → Wagtail internal:** Parse the HTML looking for `<a href="/some/path/">` tags and attempt to resolve them to Wagtail pages (by URL path), converting to `<a linktype="page" id="N">`. Unresolvable links are left as standard `<a href>` tags.

**Wagtail internal → HTML:** Use Wagtail's own `expand_db_html()` utility.

**Wagtail internal → Markdown:** Use `markdownify` or similar, with custom handlers for Wagtail's link/embed tags.

**Dependencies:** `markdown`, `markdownify` (both lightweight, pure Python).

### 4. Authentication (`auth.py`)

Leverages DRF's `TokenAuthentication` under a Django Ninja `HttpBearer` wrapper:

```python
from ninja.security import HttpBearer
from rest_framework.authtoken.models import Token

class WagtailTokenAuth(HttpBearer):
    def authenticate(self, request, token: str):
        try:
            token_obj = Token.objects.select_related('user').get(key=token)
        except Token.DoesNotExist:
            return None

        if not token_obj.user.is_active:
            return None

        request.user = token_obj.user
        return token_obj.user
```

**Setup requires** `rest_framework.authtoken` in INSTALLED_APPS (documented). Tokens are generated via the standard `./manage.py drf_create_token <username>` or Django admin.

**Future extension point:** The auth class is swappable via settings for projects that want JWT or OAuth2.

### 5. Permission Enforcement (`permissions.py`)

This is critical — the API must respect Wagtail's existing permission model exactly:

```python
from wagtail.permission_policies.pages import PagePermissionPolicy

page_permission_policy = PagePermissionPolicy()

def check_user_can_create(user, parent_page, page_type):
    """Can this user create a page of this type under this parent?"""
    # 1. Check user has 'add' permission on the parent (tree-based)
    if not page_permission_policy.user_has_permission_for_instance(
        user, 'add', parent_page
    ):
        raise PermissionDenied("No add permission on parent page")

    # 2. Check page type is allowed as a child of parent
    #    (via parent_page_types / subpage_types)
    if page_type not in parent_page.specific_class.allowed_subpage_models():
        raise ValidationError(f"{page_type} cannot be created under {parent_page.specific_class}")

def check_user_can_edit(user, page):
    """Can this user edit this specific page?"""
    perms = page.permissions_for_user(user)
    if not perms.can_edit():
        raise PermissionDenied()

def check_user_can_publish(user, page):
    """Can this user publish this page?"""
    perms = page.permissions_for_user(user)
    if not perms.can_publish():
        raise PermissionDenied()

def check_user_can_delete(user, page):
    perms = page.permissions_for_user(user)
    if not perms.can_delete():
        raise PermissionDenied()
```

**Key principle:** The API never grants capabilities beyond what the Wagtail admin would allow for the same user. Tree-based permissions propagate exactly as they do in the admin.

### 6. Pages Endpoint (`endpoints/pages.py`)

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/pages/` | List pages (filterable by type, parent, status) |
| `GET` | `/pages/{id}/` | Get single page (full detail) |
| `POST` | `/pages/` | Create a new page (as draft by default) |
| `PATCH` | `/pages/{id}/` | Update a page (creates new revision) |
| `DELETE` | `/pages/{id}/` | Delete a page |
| `POST` | `/pages/{id}/publish/` | Publish the current draft |
| `POST` | `/pages/{id}/unpublish/` | Unpublish (revert to draft) |
| `POST` | `/pages/{id}/submit-for-moderation/` | Submit for workflow moderation |
| `POST` | `/pages/{id}/copy/` | Copy a page (optionally to new parent) |
| `POST` | `/pages/{id}/move/` | Move a page to a new parent |
| `GET` | `/pages/{id}/revisions/` | List revisions |
| `GET` | `/pages/{id}/revisions/{revision_id}/` | Get specific revision |

#### Query Parameters for List

- `?type=blog.BlogPage` — filter by page type (required for type-specific fields)
- `?parent={id}` — direct children of parent
- `?descendant_of={id}` — all descendants
- `?status=draft|live|live+draft` — filter by publish status
- `?search=term` — full-text search (uses Wagtail's search backend)
- `?order=title|-first_published_at` — sort
- `?offset=0&limit=20` — pagination

#### Read Behavior (Critical for Editing)

The read endpoints are designed for **editing**, not just display. This has important implications:

**Draft-aware reads:** `GET /pages/{id}/` returns the **latest revision** content by default (i.e., the draft), not the published version. This is what a mobile editor needs — you're editing the working copy. A `?version=live` parameter can be used to explicitly request the published version.

```json
GET /pages/42/

{
  "id": 42,
  "meta": {
    "type": "blog.BlogPage",
    "status": "live+draft",
    "live": true,
    "has_unpublished_changes": true,
    "latest_revision_id": 187,
    "live_revision_id": 182,
    "first_published_at": "2026-03-01T10:00:00Z",
    "last_published_at": "2026-03-15T14:30:00Z",
    "locked": false,
    "locked_by": null,
    "parent_id": 3,
    "parent_type": "blog.BlogIndexPage",
    "children_count": 0,
    "allowed_subpage_types": [],
    "user_permissions": ["edit", "publish", "delete"]
  },
  "title": "My Blog Post (draft title)",
  "slug": "my-blog-post",
  "body": [
    {"type": "heading", "value": {"text": "Hello", "size": "h2"}, "id": "a1b2c3"},
    {"type": "paragraph", "value": "<p>Expanded HTML content</p>", "id": "d4e5f6"}
  ],
  "published_date": "2026-03-01",
  "feed_image": {
    "id": 42,
    "title": "Hero image",
    "thumbnail_url": "/media/images/hero.fill-100x100.jpg"
  },
  "authors": [
    {"id": 1, "name": "Alice", "sort_order": 0},
    {"id": 2, "name": "Bob", "sort_order": 1}
  ]
}
```

**Key read design choices:**

- **`meta.user_permissions`** tells the client what the authenticated user can do with this page — so the mobile app can show/hide publish buttons, lock indicators, etc. without making extra permission-checking requests.
- **`meta.status`** is a computed field: `"draft"` (never published), `"live"` (published, no pending changes), or `"live+draft"` (published with unpublished edits).
- **ForeignKey references** (like `feed_image`) return a summary object with `id` plus enough info for the editor UI (title, thumbnail), not just a bare integer. On write, the client sends just the integer ID.
- **Rich text in responses** uses the configured output format. For editing use cases, `"wagtail"` format is recommended (preserves internal links as IDs), while `"html"` is better if the client has no Wagtail-awareness.
- **List endpoint** returns summary fields only (title, slug, status, type, parent). Full field data requires fetching the detail endpoint with `?type=` specified.

#### Create Page Flow

```
POST /pages/
{
  "type": "blog.BlogPage",
  "parent": 3,               // parent page ID (required)
  "title": "My New Post",
  "slug": "my-new-post",     // optional — auto-generated from title
  "body": {
    "format": "markdown",
    "content": "# Hello\n\nThis is my post."
  },
  "published_date": "2026-04-03",
  "feed_image": 42            // image ID
}
```

**Server-side flow:**
1. Authenticate user via token
2. Resolve `type` → model class; validate it exists
3. Resolve `parent` → parent page instance
4. Check permissions: can user add this page type under this parent?
5. Validate body against the dynamically-generated CreateSchema for this type
6. Convert rich text fields from input format → Wagtail internal format
7. Create page instance: `parent.add_child(instance=page)`
8. Save revision: `page.save_revision()`
9. Return 201 with the created page (serialized via ReadSchema)

**The page is created as a draft by default.** To publish immediately, the client can either:
- Pass `"action": "publish"` in the request body
- Call `POST /pages/{id}/publish/` after creation

#### Update Page Flow

```
PATCH /pages/{id}/
{
  "title": "Updated Title",
  "body": {
    "format": "html",
    "content": "<p>Updated content</p>"
  }
}
```

**Server-side flow:**
1. Authenticate, load page, check edit permission
2. Validate body against PatchSchema (all fields optional)
3. Apply changes to page fields
4. Handle StreamField: merge client JSON with existing structure
5. Convert rich text fields
6. Save revision: `page.save_revision()`
7. Return 200 with updated page

### 7. Images Endpoint (`endpoints/images.py`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/images/` | List images (filterable) |
| `GET` | `/images/{id}/` | Get image detail + rendition URLs |
| `POST` | `/images/` | Upload new image (multipart/form-data) |
| `PATCH` | `/images/{id}/` | Update image metadata (title, tags, collection) |
| `DELETE` | `/images/{id}/` | Delete image |

**Upload:**

```
POST /images/
Content-Type: multipart/form-data

file: <binary>
title: "My Photo"
collection: 2        // optional collection ID
tags: "photo,nature" // comma-separated
```

**Response includes rendition URLs:**

```json
{
  "id": 42,
  "title": "My Photo",
  "width": 2000,
  "height": 1500,
  "file_url": "/media/images/my_photo.jpg",
  "renditions": {
    "thumbnail": "/media/images/my_photo.fill-100x100.jpg",
    "medium": "/media/images/my_photo.max-800x600.jpg"
  },
  "collection": {"id": 2, "name": "Photos"},
  "tags": ["photo", "nature"],
  "created_at": "2026-04-03T12:00:00Z"
}
```

**Rendition specs** are configurable in settings:

```python
WAGTAIL_CONTENT_API = {
    "IMAGE_RENDITIONS": {
        "thumbnail": "fill-100x100",
        "medium": "max-800x600",
        "large": "max-1600x1200",
    }
}
```

### 8. Schema Discovery Endpoint (`endpoints/schema_discovery.py`)

This lets clients discover what page types exist and what fields they accept:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/schema/page-types/` | List all registered page types with parent/child rules |
| `GET` | `/schema/page-types/{type}/` | Full schema for a specific type |
| `GET` | `/schema/streamfield-blocks/` | List all known StreamField block types |

**Example response for `/schema/page-types/`:**

```json
{
  "page_types": [
    {
      "type": "blog.BlogPage",
      "verbose_name": "Blog Page",
      "allowed_parent_types": ["blog.BlogIndexPage"],
      "allowed_subpage_types": [],
      "fields_summary": ["title", "slug", "body", "published_date", "feed_image", "authors"]
    },
    ...
  ]
}
```

**Example response for `/schema/page-types/blog.BlogPage/`:**

```json
{
  "type": "blog.BlogPage",
  "verbose_name": "Blog Page",
  "allowed_parent_types": ["blog.BlogIndexPage"],
  "allowed_subpage_types": [],
  "fields": {
    "title": {"type": "string", "required": true, "max_length": 255},
    "slug": {"type": "string", "required": false, "help_text": "Auto-generated if omitted"},
    "body": {
      "type": "streamfield",
      "blocks": [
        {
          "name": "heading",
          "type": "struct",
          "fields": {
            "text": {"type": "string"},
            "size": {"type": "choice", "choices": ["h2", "h3", "h4"]}
          }
        },
        {
          "name": "paragraph",
          "type": "rich_text",
          "accepts_formats": ["wagtail", "html", "markdown"]
        },
        {
          "name": "image",
          "type": "image_chooser",
          "value_type": "integer (image ID)"
        }
      ]
    },
    "published_date": {"type": "date", "required": false},
    "feed_image": {"type": "integer (image ID)", "required": false}
  }
}
```

This endpoint is also available as raw OpenAPI JSON at the standard `/api/content/v1/openapi.json` — Django Ninja generates this automatically from the Pydantic schemas.

### 9. Page Tree Operations

The API must handle Wagtail's tree structure (built on `django-treebeard`):

**Create** always requires `parent` — there is no concept of a root-level page creation via the API (the root page is a Wagtail internal concept).

**Move** uses treebeard's `move()` under the hood:

```
POST /pages/{id}/move/
{
  "destination": 5,           // new parent page ID
  "position": "last-child"    // or "first-child", "left", "right"
}
```

**Copy** creates a full deep copy:

```
POST /pages/{id}/copy/
{
  "destination": 5,           // new parent page ID
  "recursive": true,          // copy descendants
  "update_slug": true,        // auto-modify slug to avoid collision
  "publish_copies": false     // keep copies as draft
}
```

---

## Implementation Phases

### Phase 1: Foundation (est. 2–3 days)

- [ ] Project scaffolding: pyproject.toml, src layout, Makefile
- [ ] Example project: `example/` with settings, urls, wsgi
- [ ] Test models in `example/testapp/`: SimplePage, BlogPage (with StreamField + Orderables), EventPage
- [ ] `seed_demo` management command: creates users, page tree, tokens, sample images
- [ ] Django Ninja API instance with HttpBearer auth (DRF tokens)
- [ ] Basic schema generator: simple Django fields only (CharField, IntegerField, DateField, BooleanField, ForeignKey)
- [ ] Read endpoints: `GET /pages/` and `GET /pages/{id}/` with draft-aware reads
- [ ] Schema discovery: `GET /schema/page-types/`
- [ ] Pytest conftest wired to example project; first passing tests

### Phase 2: Write Operations (est. 2–3 days)

- [ ] Create page: `POST /pages/` with parent, type, and simple fields
- [ ] Update page: `PATCH /pages/{id}/`
- [ ] Delete page: `DELETE /pages/{id}/`
- [ ] Permission enforcement for all write operations
- [ ] Slug auto-generation
- [ ] Revision creation on every write

### Phase 3: StreamField (est. 3–4 days)

- [ ] StreamField schema generation (CharBlock, RichTextBlock, IntegerBlock, ImageChooserBlock, PageChooserBlock)
- [ ] StructBlock → nested Pydantic model generation
- [ ] ListBlock support
- [ ] Nested StreamBlock support
- [ ] StreamField read serialization
- [ ] StreamField write deserialization + validation
- [ ] Round-trip tests (read → modify → write → read)

### Phase 4: Rich Text (est. 2 days)

- [ ] RichTextInput schema with format field
- [ ] HTML → Wagtail internal converter (link resolution by path)
- [ ] Markdown → Wagtail internal converter (with `wagtail://page/N` syntax)
- [ ] Wagtail internal → HTML (using `expand_db_html`)
- [ ] Wagtail internal → Markdown
- [ ] Configurable output format in settings
- [ ] Tests for all conversion paths including edge cases (nested formatting, images in rich text)

### Phase 5: Workflow + Advanced Operations (est. 2–3 days)

- [ ] Publish / Unpublish endpoints
- [ ] Submit for moderation (integrates with Wagtail Workflows)
- [ ] Revision listing and detail endpoints
- [ ] Copy and Move endpoints
- [ ] Draft preview support (return draft content vs live content)

### Phase 6: Images (est. 1–2 days)

- [ ] Image list / detail endpoints
- [ ] Image upload (multipart/form-data)
- [ ] Image update (title, tags, collection)
- [ ] Image delete
- [ ] Rendition URL generation
- [ ] Collection-based permissions for images

### Phase 7: Polish + Release (est. 2–3 days)

- [ ] OpenAPI schema review and cleanup
- [ ] Error response standardization (consistent error format)
- [ ] Rate limiting hooks
- [ ] Documentation (README, full usage guide)
- [ ] CI: tox, GitHub Actions, test matrix (Wagtail 6.x + 7.x, Python 3.10+)
- [ ] PyPI release

---

## Key Technical Challenges & Solutions

### Challenge 1: Dynamic Schema Generation at Scale

**Problem:** A Wagtail site might have 50+ page types. Generating Pydantic schemas dynamically for all of them on every request would be slow.

**Solution:** Generate schemas once at Django startup (in `AppConfig.ready()`) and cache them in a registry. The registry maps `"app_label.ModelName"` → `(ReadSchema, CreateSchema, PatchSchema)`. Django Ninja route handlers look up the schema from the registry based on the `?type=` parameter.

```python
# schema/registry.py
class SchemaRegistry:
    _schemas = {}

    @classmethod
    def register(cls, model_class):
        key = f"{model_class._meta.app_label}.{model_class.__name__}"
        cls._schemas[key] = generate_schemas_for_model(model_class)

    @classmethod
    def auto_discover(cls):
        from wagtail.models import Page
        for model in Page.__subclasses__():  # recursive
            if not model._meta.abstract:
                cls.register(model)
```

### Challenge 2: StreamField Validation

**Problem:** StreamField blocks can be deeply nested (StreamBlock containing StructBlock containing ListBlock containing StructBlock...). The validation schema must mirror this.

**Solution:** Recursive schema generation with memoization to handle blocks that reference each other. Each block type maps to a Pydantic schema with a discriminator on the `type` field:

```python
from pydantic import Discriminator, Tag
from typing import Annotated, Union

# For a StreamField with heading, paragraph, image blocks:
StreamBlockItem = Annotated[
    Union[
        Annotated[HeadingBlockSchema, Tag("heading")],
        Annotated[ParagraphBlockSchema, Tag("paragraph")],
        Annotated[ImageBlockSchema, Tag("image")],
    ],
    Discriminator("type")
]
```

### Challenge 3: Rich Text Internal Links

**Problem:** Wagtail stores links as `<a linktype="page" id="5">` which is meaningless to API clients sending markdown or HTML.

**Solution:** The conversion layer handles this bidirectionally:
- **Inbound HTML:** Scan for `<a href="/some/path/">` and resolve via `Page.objects.filter(url_path=...)`. Unresolvable links stay as `href`.
- **Inbound Markdown:** Support `wagtail://page/5` for explicit ID references, and `[text](/path/)` for path-based resolution.
- **Outbound:** Convert to standard `<a href>` by default (using `expand_db_html`), or return raw Wagtail format if configured.

### Challenge 4: Orderable / InlinePanel Children

**Problem:** Wagtail pages often have child models (via `InlinePanel`) like `BlogPageAuthor` or `BlogPageTag`. These need to be writable too.

**Solution:** Introspect `ParentalKey` relationships pointing to the page model. For each, generate a nested schema. On create/update, the API accepts a list of child objects:

```json
{
  "type": "blog.BlogPage",
  "parent": 3,
  "title": "My Post",
  "authors": [
    {"name": "Alice", "sort_order": 0},
    {"name": "Bob", "sort_order": 1}
  ]
}
```

On update, the semantics are **replace** — the client sends the full desired list, and the server diffs against existing children (deleting removed, creating new, updating changed).

---

## Error Response Format

All errors follow a consistent structure:

```json
{
  "error": "validation_error",
  "message": "Invalid data for field 'body'",
  "details": [
    {
      "field": "body[2].value.text",
      "message": "This field is required",
      "code": "required"
    }
  ]
}
```

HTTP status codes:
- `400` — Validation error
- `401` — Authentication required
- `403` — Permission denied (with specific reason)
- `404` — Page/image not found
- `409` — Conflict (e.g., slug already exists under parent)
- `422` — Unprocessable (e.g., page type not allowed under parent)

---

## Testing Strategy

All tests use the models defined in `example/testapp/` — there is no separate set of test models. The `conftest.py` adds `example/` to the Python path and configures Django settings to use `example_project.settings`.

- **Unit tests:** Schema generation for every field type, rich text conversion, permission checks
- **Integration tests:** Full request/response cycles for all endpoints using Django's test client
- **Test models:** `SimplePage`, `BlogPage` (kitchen-sink StreamField + Orderables), `EventPage` (date fields, write_api_exclude) — see the model definitions in the Package Structure section above
- **Round-trip tests:** `GET` a page → modify the JSON → `PATCH` it back → `GET` again → assert no data loss. These are the most important tests and should cover every field type including nested StreamField blocks.
- **Permission matrix tests:** For each endpoint, test with admin, editor (add/edit only), moderator (add/edit/publish), and an unauthenticated request. Verify that an editor cannot publish, a moderator cannot edit pages outside their tree, etc.
- **Seed data in CI:** The `seed_demo` command runs in CI setup so integration tests operate on a realistic page tree, not just isolated factory-created pages
- **Compatibility:** Tox matrix covering Wagtail 6.x + 7.x, Python 3.10+

---

## Dependencies

```toml
[project]
requires-python = ">=3.10"
dependencies = [
    "wagtail>=6.0",
    "django-ninja>=1.0",
    "djangorestframework",         # for TokenAuthentication only
    "markdown>=3.5",               # markdown → HTML conversion
    "markdownify>=0.11",           # HTML → markdown conversion
]
```

---

## Future Extensions (v2+)

- **Documents endpoint** — CRUD for Wagtail documents
- **Snippets endpoint** — Generic CRUD for registered snippet models
- **Webhook support** — Notify external systems on page publish/unpublish
- **JWT authentication** — via `django-ninja-jwt`
- **Bulk operations** — Create/update multiple pages in one request
- **Content staging** — Compare draft vs live content
- **Audit log** — Track all API mutations with user/timestamp
- **GraphQL alternative** — Optional GraphQL schema generated from the same introspection layer
