# Schema Discovery API

Discover what page types exist, what fields they accept, and their parent/child constraints. Useful for building dynamic editors that adapt to the site's content model.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/schema/page-types/` | List all page types |
| `GET` | `/schema/page-types/{type}/` | Full schema for a page type |

---

## List page types

```
GET /schema/page-types/
```

### Response

```json
{
  "page_types": [
    {
      "type": "blog.BlogPage",
      "verbose_name": "blog page",
      "allowed_parent_types": ["blog.BlogIndexPage"],
      "allowed_subpage_types": [],
      "fields_summary": ["id", "title", "slug", "published_date", "body", "authors"]
    },
    {
      "type": "blog.BlogIndexPage",
      "verbose_name": "blog index page",
      "allowed_parent_types": ["wagtailcore.Page", "home.HomePage"],
      "allowed_subpage_types": ["blog.BlogPage"],
      "fields_summary": ["id", "title", "slug", "intro"]
    }
  ]
}
```

The `allowed_parent_types` and `allowed_subpage_types` reflect the page model's `parent_page_types` and `subpage_types` attributes. Use these to build a valid page creation UI -- a client knows which page types can be created under a given parent.

---

## Get page type schema

```
GET /schema/page-types/blog.BlogPage/
```

Returns the full JSON Schema for the create, patch, and read schemas:

```json
{
  "type": "blog.BlogPage",
  "create_schema": {
    "title": "BlogPageCreate",
    "type": "object",
    "properties": {
      "type": {"type": "string"},
      "parent": {"type": "integer"},
      "title": {"type": "string"},
      "slug": {"anyOf": [{"type": "string"}, {"type": "null"}]},
      "published_date": {"anyOf": [{"type": "string", "format": "date"}, {"type": "null"}]},
      "body": {"type": "array"},
      "authors": {"type": "array"}
    },
    "required": ["type", "parent", "title"]
  },
  "patch_schema": { ... },
  "read_schema": { ... }
}
```

These schemas are the Pydantic models' JSON Schema representation, generated automatically from your Wagtail page models.

---

## OpenAPI specification

Django Ninja also generates a full OpenAPI 3.x specification at:

```
GET /api/write/v1/openapi.json
```

This can be imported into tools like Postman, Insomnia, or used to generate client SDKs.
