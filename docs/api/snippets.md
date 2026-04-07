# Snippets API

Create, list, update, and delete Wagtail snippets -- models registered with `@register_snippet`. Snippets are flat (no tree hierarchy), have no draft/publish workflow, and have no revisions.

Unlike pages, each snippet model lives in its own database table, so the `type` parameter is **required** on every endpoint.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/snippets/` | List snippets |
| `GET` | `/snippets/{id}/` | Get snippet detail |
| `POST` | `/snippets/` | Create a snippet |
| `PATCH` | `/snippets/{id}/` | Update a snippet |
| `DELETE` | `/snippets/{id}/` | Delete a snippet |

---

## List snippets

```
GET /snippets/?type=testapp.Category
```

The `type` query parameter is **required**. Returns `422` if missing or unrecognised.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | **Yes** | Snippet type (e.g. `testapp.Category`) |
| `search` | string | No | Filter by name/title |
| `offset` | int | No | Pagination offset |
| `limit` | int | No | Items per page |

### Response

```json
{
  "items": [
    {
      "id": 1,
      "meta": {"type": "testapp.Category"},
      "name": "Technology",
      "slug": "technology"
    },
    {
      "id": 2,
      "meta": {"type": "testapp.Category"},
      "name": "Science",
      "slug": "science"
    }
  ],
  "meta": {
    "total_count": 2
  }
}
```

---

## Get snippet detail

```
GET /snippets/{id}/?type=testapp.Category
```

Returns the same fields as the list item.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | **Yes** | Snippet type |

Returns `404` if the snippet does not exist.

---

## Create a snippet

```
POST /snippets/
Content-Type: application/json
```

### Request body

```json
{
  "type": "testapp.Category",
  "name": "Music",
  "slug": "music"
}
```

The `type` field is **required** in the request body.

### Response

`201 Created` with the snippet detail.

### Example

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"type": "testapp.Category", "name": "Music", "slug": "music"}' \
     http://localhost:8000/api/write/v1/snippets/ | python -m json.tool
```

---

## Update a snippet

```
PATCH /snippets/{id}/?type=testapp.Category
Content-Type: application/json
```

Partial update -- only send the fields you want to change.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | **Yes** | Snippet type |

### Request body

```json
{
  "name": "Music & Arts"
}
```

### Response

`200 OK` with the updated snippet detail.

---

## Delete a snippet

```
DELETE /snippets/{id}/?type=testapp.Category
```

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | **Yes** | Snippet type |

Returns `204 No Content` on success, `404` if not found.

---

## Error responses

| Status | Meaning |
|--------|---------|
| `400` | Django validation error (e.g. blank required field, unique constraint) |
| `401` | Missing or invalid authentication token |
| `404` | Snippet not found |
| `422` | Missing or unrecognised `type`, invalid field data |

---

## Field handling

Snippet fields are handled the same way as page fields:

- **StreamField** values are read and written as block lists
- **RichTextField** values accept Markdown, HTML, or Wagtail internal format
- **ForeignKey** fields accept the related object's ID
- **CharField**, **SlugField**, etc. accept their natural types

See the [Schema Discovery API](schema-discovery.md) for how to inspect a snippet type's fields at runtime.
