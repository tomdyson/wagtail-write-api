# Workflow

The API supports Wagtail's full content lifecycle: create as draft, edit, publish, unpublish, and track revision history.

## Page lifecycle

```
Create (draft) → Edit → Publish → Edit (new draft) → Publish again
                                 → Unpublish (revert to draft)
```

## Creating content

Pages are created as **drafts** by default:

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"type": "blog.BlogPage", "parent": 3, "title": "New Post"}' \
     http://localhost:8000/api/write/v1/pages/
```

The response shows `"live": false`. The page exists in the tree but isn't publicly visible.

### Publish on create

Add `"action": "publish"` to create and publish in one request:

```json
{
  "type": "blog.BlogPage",
  "parent": 3,
  "title": "New Post",
  "action": "publish"
}
```

## Editing and revisions

Every `PATCH` creates a new revision:

```bash
curl -X PATCH \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Updated Title"}' \
     http://localhost:8000/api/write/v1/pages/5/
```

The revision is saved but the page is **not automatically published**. The page now has `"has_unpublished_changes": true`.

### Publish after editing

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/5/publish/
```

### Edit + publish in one request

```json
{
  "title": "Updated and Published",
  "action": "publish"
}
```

## Draft vs live content

The detail endpoint is **draft-aware**:

| Request | Returns |
|---------|---------|
| `GET /pages/5/` | Latest draft (revision) content |
| `GET /pages/5/?version=live` | Published content |

When a page has no unpublished changes, both return the same data.

This distinction is important for editors: the user is editing the working copy, not the published version. The `meta.status` fields indicate the current state:

```json
{
  "meta": {
    "live": true,
    "has_unpublished_changes": true
  }
}
```

| `live` | `has_unpublished_changes` | Status |
|--------|--------------------------|--------|
| `false` | `true` | Draft (never published) |
| `true` | `false` | Published, up to date |
| `true` | `true` | Published with pending draft changes |

## Revision history

List all revisions for a page:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/5/revisions/
```

```json
{
  "items": [
    {"id": 42, "created_at": "2026-03-15T14:30:00", "user": "admin"},
    {"id": 41, "created_at": "2026-03-14T10:00:00", "user": "editor"},
    {"id": 40, "created_at": "2026-03-13T09:00:00", "user": "admin"}
  ]
}
```

View a specific revision's content:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/5/revisions/41/
```

This returns the full page detail as it was at that revision.

## Unpublishing

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/5/unpublish/
```

The page reverts to draft status (`"live": false`). Its content is preserved but it's no longer publicly visible.

## Copying pages

Create a deep copy of a page (and optionally its descendants):

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"destination": 2, "recursive": true}' \
     http://localhost:8000/api/write/v1/pages/5/copy/
```

The copy is created as a draft with a unique slug. Returns `201` with the new page.

## Moving pages

Move a page to a new position in the tree:

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"destination": 10, "position": "last-child"}' \
     http://localhost:8000/api/write/v1/pages/5/move/
```

!!! warning
    Moving a page changes its URL path (and the URL paths of all descendants). Wagtail handles this internally, but API clients and cached URLs should be aware of this.
