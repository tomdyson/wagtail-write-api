# Schema Discovery API

Discover what page types and snippet types exist, what fields they accept, and their constraints. Useful for building dynamic editors that adapt to the site's content model.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/schema/` | List all page types |
| `GET` | `/schema/{type}/` | Full schema for a page type |
| `GET` | `/schema/snippets/` | List all snippet types |
| `GET` | `/schema/snippets/{type}/` | Full schema for a snippet type |

---

## List page types

```
GET /schema/
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
      "fields_summary": ["id", "title", "slug", "published_date", "body", "authors"],
      "available_parents": [
        {"id": 3, "title": "Blog", "type": "blog.BlogIndexPage", "url_path": "/blog/"}
      ]
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

The `allowed_parent_types` and `allowed_subpage_types` reflect the page model's `parent_page_types` and `subpage_types` attributes (both directions of the constraint are checked). The `available_parents` field lists actual page instances (up to 10 per parent type) that can serve as parents, including their `id`, `title`, `type`, and `url_path`. This allows clients to skip a separate `pages list` call when creating pages — the parent ID is already available in the schema response.

`available_parents` is only present when the page type has a real constraint (i.e. `wagtailcore.Page` is not among its allowed parents). For unconstrained types the field is omitted entirely — almost every page qualifies, so listing instances would be noise rather than signal. If you need to find a parent for an unconstrained type, use the `GET /pages/` endpoint with a `type` filter.

---

## Get page type schema

```
GET /schema/blog.BlogPage/
```

Returns the full JSON Schema for the create, patch, and read schemas, plus detailed StreamField block definitions:

```json
{
  "type": "blog.BlogPage",
  "create_schema": {
    "title": "BlogPageCreate",
    "type": "object",
    "properties": {
      "type": {"type": "string"},
      "parent": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
      "title": {"type": "string"},
      "slug": {"anyOf": [{"type": "string"}, {"type": "null"}]},
      "published_date": {"anyOf": [{"type": "string", "format": "date"}, {"type": "null"}]},
      "body": {"type": "array"},
      "authors": {"type": "array"}
    },
    "required": ["type", "parent", "title"]
  },
  "patch_schema": { ... },
  "read_schema": { ... },
  "streamfield_blocks": {
    "body": [
      {
        "type": "heading",
        "schema": {
          "type": "object",
          "properties": {
            "text": {"type": "string", "required": true},
            "size": {"type": "string", "enum": ["h2", "h3", "h4"], "required": true}
          }
        }
      },
      {
        "type": "paragraph",
        "schema": {"type": "richtext"}
      },
      {
        "type": "image",
        "schema": {"type": "image_chooser"}
      },
      {
        "type": "gallery",
        "schema": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "image": {"type": "image_chooser", "required": true},
              "caption": {"type": "string", "required": false}
            }
          }
        }
      }
    ]
  }
}
```

The `create_schema`, `patch_schema`, and `read_schema` are Pydantic-generated JSON Schemas. The `streamfield_blocks` section provides detailed block type definitions for each StreamField on the model, including nested StructBlock properties, ListBlock item schemas, ChoiceBlock enums, and chooser block types. For page types with no StreamFields, `streamfield_blocks` is an empty object.

### Block schema types

| Schema type | Meaning |
|-------------|---------|
| `string` | CharBlock, TextBlock |
| `richtext` | RichTextBlock (accepts HTML or Markdown) |
| `integer` | IntegerBlock |
| `float` | FloatBlock |
| `boolean` | BooleanBlock |
| `date` | DateBlock |
| `datetime` | DateTimeBlock |
| `url` | URLBlock |
| `email` | EmailBlock |
| `image_chooser` | ImageChooserBlock (value is an image ID) |
| `page_chooser` | PageChooserBlock (value is a page ID) |
| `object` | StructBlock (has `properties` with child block schemas) |
| `array` | ListBlock (has `items` with the child block schema) |
| `streamfield` | Nested StreamBlock (has `block_types` list) |

---

## List snippet types

```
GET /schema/snippets/
```

### Response

```json
{
  "snippet_types": [
    {
      "type": "testapp.Category",
      "verbose_name": "category",
      "fields_summary": ["name", "slug", "id"]
    },
    {
      "type": "testapp.Tag",
      "verbose_name": "tag",
      "fields_summary": ["name", "id"]
    }
  ]
}
```

Snippet types are simpler than page types -- no `allowed_parent_types`, `allowed_subpage_types`, or `available_parents` since snippets have no tree hierarchy.

---

## Get snippet type schema

```
GET /schema/snippets/testapp.Category/
```

Returns the same schema structure as page types, but `create_schema` does not include `parent` or `action` fields (snippets have no tree or publish workflow):

```json
{
  "type": "testapp.Category",
  "create_schema": {
    "title": "CategoryCreate",
    "type": "object",
    "properties": {
      "type": {"type": "string"},
      "name": {"type": "string"},
      "slug": {"anyOf": [{"type": "string"}, {"type": "null"}]}
    },
    "required": ["type", "name"]
  },
  "patch_schema": { ... },
  "read_schema": { ... },
  "streamfield_blocks": {},
  "richtext_fields": []
}
```

Returns `404` if the snippet type is not registered.

---

## OpenAPI specification

Django Ninja also generates a full OpenAPI 3.x specification at:

```
GET /api/write/v1/openapi.json
```

This can be imported into tools like Postman, Insomnia, or used to generate client SDKs.
