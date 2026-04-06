# Quickstart

A complete walkthrough: install the plugin, create a page via the API, publish it, and read it back.

## 1. Set up

Follow the [Installation](installation.md) instructions, then create a token:

```bash
python manage.py drf_create_token admin
```

Save the token for the examples below. We'll use `$TOKEN` as a placeholder.

## 2. List pages

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/ | python -m json.tool
```

```json
{
    "items": [
        {
            "id": 2,
            "title": "Home",
            "slug": "home",
            "meta": {
                "type": "wagtailcore.Page",
                "live": true,
                "has_unpublished_changes": false,
                "parent_id": 1
            }
        }
    ],
    "meta": {
        "total_count": 1
    }
}
```

## 3. Create a page

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "type": "myapp.SimplePage",
       "parent": 2,
       "title": "Hello from the API",
       "body": {
         "format": "markdown",
         "content": "This page was created via the **write API**."
       }
     }' \
     http://localhost:8000/api/write/v1/pages/ | python -m json.tool
```

The response returns the created page with `"live": false` -- it's a draft by default.

## 4. Publish the page

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/3/publish/ | python -m json.tool
```

The page is now live. You can also publish on creation by adding `"action": "publish"` to the POST body.

## 5. Update the page

```bash
curl -s -X PATCH \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Updated title"}' \
     http://localhost:8000/api/write/v1/pages/3/ | python -m json.tool
```

PATCH creates a new revision. Only the fields you send are updated; others are preserved.

## 6. Read the page detail

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/3/ | python -m json.tool
```

By default, the detail endpoint returns the latest draft content. Add `?version=live` to get the published version instead.

## 7. Upload an image

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@photo.jpg" \
     -F "title=My Photo" \
     http://localhost:8000/api/write/v1/images/ | python -m json.tool
```

## 8. Delete a page

```bash
curl -s -X DELETE \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/3/
```

Returns `204 No Content` on success.

## Next steps

- [Configuration](configuration.md) -- customise settings
- [Pages API](../api/pages.md) -- full endpoint reference
- [Rich text guide](../guides/rich-text.md) -- Markdown, HTML, and Wagtail format
- [StreamField guide](../guides/streamfield.md) -- working with StreamField data
