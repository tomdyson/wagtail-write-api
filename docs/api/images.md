# Images API

Upload, list, update, and delete images. Responses include rendition URLs for common sizes.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/images/` | List images |
| `GET` | `/images/{id}/` | Get image detail |
| `POST` | `/images/` | Upload an image |
| `PATCH` | `/images/{id}/` | Update metadata |
| `DELETE` | `/images/{id}/` | Delete an image |

---

## List images

```
GET /images/
```

### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Filter by title |
| `offset` | int | Pagination offset |
| `limit` | int | Items per page |

### Response

```json
{
  "items": [
    {
      "id": 1,
      "title": "Hero image",
      "width": 2000,
      "height": 1500,
      "file_url": "/media/images/hero.jpg",
      "created_at": "2026-03-01T12:00:00",
      "renditions": {
        "thumbnail": "/media/images/hero.fill-100x100.jpg",
        "medium": "/media/images/hero.max-800x600.jpg",
        "large": "/media/images/hero.max-1600x1200.jpg"
      }
    }
  ],
  "meta": {
    "total_count": 15
  }
}
```

---

## Get image detail

```
GET /images/{id}/
```

Returns the same fields as the list item, including all configured rendition URLs.

---

## Upload an image

```
POST /images/
Content-Type: multipart/form-data
```

| Field | Required | Description |
|-------|----------|-------------|
| `file` | Yes | The image file |
| `title` | No | Image title (defaults to filename) |

### Example

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@photo.jpg" \
     -F "title=My Photo" \
     http://localhost:8000/api/write/v1/images/
```

### Response

`201 Created` with the image detail including rendition URLs.

---

## Update image metadata

```
PATCH /images/{id}/
Content-Type: application/json
```

```json
{
  "title": "Updated title"
}
```

---

## Delete an image

```
DELETE /images/{id}/
```

Returns `204 No Content` on success.

---

## Renditions

Rendition URLs are generated based on the `IMAGE_RENDITIONS` setting. The default configuration produces three sizes:

| Name | Spec | Description |
|------|------|-------------|
| `thumbnail` | `fill-100x100` | Square crop, 100px |
| `medium` | `max-800x600` | Fit within 800x600 |
| `large` | `max-1600x1200` | Fit within 1600x1200 |

Customise these in your settings:

```python title="settings.py"
WAGTAIL_WRITE_API = {
    "IMAGE_RENDITIONS": {
        "small": "fill-200x200",
        "hero": "max-1920x1080",
    }
}
```

See [Wagtail's image rendition docs](https://docs.wagtail.org/en/stable/topics/images.html#generating-renditions-in-python) for available filter specs.
