# Pages API

Full CRUD for Wagtail pages with draft/publish workflow, tree operations, and revision history.

!!! note
    All API URLs require a trailing slash (e.g. `/pages/`, `/pages/3/`). Requests without one will receive a `301` redirect. This follows the standard Django URL convention.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/pages/` | List pages |
| `GET` | `/pages/{id}/` | Get page detail |
| `POST` | `/pages/` | Create a page |
| `PATCH` | `/pages/{id}/` | Update a page |
| `DELETE` | `/pages/{id}/` | Delete a page |
| `POST` | `/pages/{id}/publish/` | Publish |
| `POST` | `/pages/{id}/unpublish/` | Unpublish |
| `POST` | `/pages/{id}/copy/` | Copy a page |
| `POST` | `/pages/{id}/move/` | Move a page |
| `GET` | `/pages/{id}/revisions/` | List revisions |
| `GET` | `/pages/{id}/revisions/{rev_id}/` | Get revision detail |

---

## List pages

```
GET /pages/
```

### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | Filter by page type, e.g. `blog.BlogPage` |
| `parent` | int or string | Direct children of this page ID or URL path (e.g. `5` or `/blog/`) |
| `descendant_of` | int or string | All descendants of this page ID or URL path |
| `status` | string | `draft`, `live`, or `live+draft` |
| `slug` | string | Exact slug match (may return multiple if slug exists under different parents) |
| `path` | string | Exact URL path match, e.g. `/blog/my-post/` (always 0 or 1 result) |
| `search` | string | Full-text search |
| `order` | string | Sort field, e.g. `title` or `-first_published_at` |
| `offset` | int | Pagination offset (default: 0) |
| `limit` | int | Items per page (default: 20, max: 100) |

### Response

```json
{
  "items": [
    {
      "id": 5,
      "title": "My Blog Post",
      "slug": "my-blog-post",
      "meta": {
        "type": "blog.BlogPage",
        "live": true,
        "has_unpublished_changes": false,
        "parent_id": 3
      }
    }
  ],
  "meta": {
    "total_count": 42
  }
}
```

The list endpoint returns summary fields only. Use the detail endpoint for full field data.

---

## Get page detail

```
GET /pages/{id}/
```

### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `version` | string | Set to `live` to get the published version instead of the draft |

### Draft-aware reads

By default, the detail endpoint returns the **latest revision** content (the working draft). This is what an editor needs -- you're editing the most recent version, not necessarily what's published.

If the page has no unpublished changes, the draft and live content are identical.

### Response

```json
{
  "id": 5,
  "title": "My Blog Post",
  "slug": "my-blog-post",
  "published_date": "2026-03-01",
  "body": [
    {
      "type": "heading",
      "value": {"text": "Hello", "size": "h2"},
      "id": "a1b2c3d4"
    },
    {
      "type": "paragraph",
      "value": "<p>Some content</p>",
      "id": "e5f6g7h8"
    }
  ],
  "authors": [
    {"id": 1, "name": "Alice", "sort_order": 0}
  ],
  "meta": {
    "type": "blog.BlogPage",
    "live": true,
    "has_unpublished_changes": true,
    "first_published_at": "2026-03-01T10:00:00",
    "last_published_at": "2026-03-15T14:30:00",
    "parent_id": 3,
    "parent_type": "blog.BlogIndexPage",
    "children_count": 0,
    "user_permissions": ["add", "change", "publish", "delete"]
  },
  "hints": {
    "publish": "wagapi pages publish 5",
    "unpublish": "wagapi pages unpublish 5",
    "edit": "wagapi pages update 5 --title '...' --field 'body:...'",
    "view": "wagapi pages get 5",
    "delete": "wagapi pages delete 5"
  }
}
```

!!! note "`meta.user_permissions`"
    Tells the client what the authenticated user can do with this page. A mobile app can use this to show/hide publish buttons, lock indicators, etc. without extra permission-checking requests.

!!! note "`hints`"
    The `hints` object provides ready-to-use CLI commands for common next actions. This is designed for LLM orchestration — an agent can read the hints and immediately know what command to run next without constructing it from scratch. The `publish` hint is only present when the page is unpublished or has unpublished changes.

---

## Create a page

```
POST /pages/
Content-Type: application/json
```

### Request body

```json
{
  "type": "blog.BlogPage",
  "parent": 3,
  "title": "My New Post",
  "slug": "my-new-post",
  "body": [
    {
      "type": "paragraph",
      "value": "<p>Content here</p>",
      "id": "unique-uuid"
    }
  ],
  "authors": [
    {"name": "Alice", "role": "Writer"}
  ],
  "action": "publish"
}
```

The `parent` field also accepts a URL path string, which the server resolves to a page ID:

```json
{
  "type": "blog.BlogPage",
  "parent": "/blog/",
  "title": "My New Post"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Page type as `app_label.ModelName` |
| `parent` | Yes | Parent page ID (integer) or URL path (string, e.g. `"/blog/"`) |
| `title` | Yes | Page title |
| `slug` | No | Auto-generated from title if omitted |
| `action` | No | Set to `"publish"` to publish immediately |

Pages are created as **drafts** by default.

### Response

`201 Created` with the full page detail.

---

## Update a page

```
PATCH /pages/{id}/
Content-Type: application/json
```

Send only the fields you want to update. All fields are optional.

```json
{
  "title": "Updated Title",
  "body": [
    {
      "type": "paragraph",
      "value": "<p>Updated content</p>",
      "id": "e5f6g7h8"
    }
  ]
}
```

Every update creates a **new revision**. The page is not automatically published -- add `"action": "publish"` to publish the changes.

### Orderable children

For fields like `authors` (InlinePanel/Orderable), send the complete desired list. The API replaces all existing children with the new list.

```json
{
  "authors": [
    {"name": "Alice", "role": "Lead"},
    {"name": "Charlie", "role": "Contributor"}
  ]
}
```

---

## Delete a page

```
DELETE /pages/{id}/
```

Returns `204 No Content` on success.

---

## Publish / Unpublish

```
POST /pages/{id}/publish/
POST /pages/{id}/unpublish/
```

Publish makes the latest revision live. Unpublish reverts the page to draft status.

---

## Copy a page

```
POST /pages/{id}/copy/
Content-Type: application/json
```

```json
{
  "destination": 5,
  "recursive": true
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `destination` | required | New parent page ID |
| `recursive` | `true` | Copy descendants too |

Returns `201 Created` with the new page. A unique slug is generated automatically.

---

## Move a page

```
POST /pages/{id}/move/
Content-Type: application/json
```

```json
{
  "destination": 5,
  "position": "last-child"
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `destination` | required | New parent page ID |
| `position` | `"last-child"` | `first-child`, `last-child`, `left`, or `right` |

---

## Revisions

```
GET /pages/{id}/revisions/
```

Returns a list of all revisions for the page:

```json
{
  "items": [
    {"id": 42, "created_at": "2026-03-15T14:30:00", "user": "admin"},
    {"id": 41, "created_at": "2026-03-14T10:00:00", "user": "editor"}
  ]
}
```

Get a specific revision's content:

```
GET /pages/{id}/revisions/{rev_id}/
```

Returns the page detail as it was at that revision.

---

## Error responses

All errors follow a consistent format:

```json
{
  "error": "validation_error",
  "message": "BlogPage cannot be created under SimplePage",
  "details": [...]
}
```

| Status | Meaning |
|--------|---------|
| `400` | Validation error |
| `401` | Authentication required |
| `403` | Permission denied |
| `404` | Page not found |
| `422` | Unprocessable (e.g. invalid page type under parent) |
