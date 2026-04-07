# Configuration

All settings are optional. The API works out of the box with sensible defaults.

## Settings

Add a `WAGTAIL_WRITE_API` dictionary to your Django settings:

```python title="settings.py"
WAGTAIL_WRITE_API = {
    "RICH_TEXT_OUTPUT_FORMAT": "html",
    "EXCLUDE_PAGE_TYPES": [],
    "EXCLUDE_SNIPPET_TYPES": [],
    "DOCS_URL": "/docs",
    "REQUIRE_AUTH_FOR_READ": True,
    "DEFAULT_PAGE_SIZE": 20,
    "MAX_PAGE_SIZE": 100,
    "IMAGE_RENDITIONS": {
        "thumbnail": "fill-100x100",
        "medium": "max-800x600",
        "large": "max-1600x1200",
    },
}
```

## Reference

### `RICH_TEXT_OUTPUT_FORMAT`

**Default:** `"html"`

Controls the format used for rich text fields in GET responses.

| Value | Description |
|-------|-------------|
| `"html"` | Standard HTML with links expanded to real URLs |
| `"wagtail"` | Wagtail's internal format (preserves `linktype="page"` etc.) |
| `"markdown"` | Converted to Markdown |

For mobile CMS editors that need to round-trip content, use `"wagtail"`. For display-only clients, `"html"` is simplest.

### `EXCLUDE_PAGE_TYPES`

**Default:** `[]`

A list of page type strings to exclude from the API entirely. These types won't appear in schema discovery or be available for CRUD operations.

```python
"EXCLUDE_PAGE_TYPES": ["myapp.InternalPage", "myapp.LandingPage"]
```

### `EXCLUDE_SNIPPET_TYPES`

**Default:** `[]`

A list of snippet type strings to exclude from the API entirely. These types won't appear in schema discovery or be available for CRUD operations.

```python
"EXCLUDE_SNIPPET_TYPES": ["myapp.InternalTag"]
```

### `DOCS_URL`

**Default:** `"/docs"`

The URL path for the interactive OpenAPI documentation. Set to `None` to disable the docs endpoint.

### `REQUIRE_AUTH_FOR_READ`

**Default:** `True`

When `True`, all endpoints (including GET) require authentication. Set to `False` to allow unauthenticated read access.

### `DEFAULT_PAGE_SIZE`

**Default:** `20`

The default number of items returned in list endpoints when no `limit` parameter is provided.

### `MAX_PAGE_SIZE`

**Default:** `100`

The maximum allowed value for the `limit` parameter. Requests for more items than this are clamped.

### `IMAGE_RENDITIONS`

**Default:**
```python
{
    "thumbnail": "fill-100x100",
    "medium": "max-800x600",
    "large": "max-1600x1200",
}
```

A dictionary of rendition name to [Wagtail rendition spec](https://docs.wagtail.org/en/stable/topics/images.html#generating-renditions-in-python). These renditions are generated and their URLs included in image detail responses.

## Excluding fields from the API

Individual page models can exclude specific fields using the `write_api_exclude` attribute:

```python title="models.py"
class EventPage(Page):
    start_date = models.DateTimeField()
    legacy_id = models.CharField(max_length=50, blank=True)

    # This field won't appear in the API
    write_api_exclude = ["legacy_id"]
```
