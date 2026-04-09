# StreamField

StreamField data is represented as a list of blocks, where each block has a `type`, `value`, and `id`. This format matches Wagtail's internal JSON storage, enabling full round-trip editing without data loss.

## Reading StreamField data

```json
{
  "body": [
    {
      "type": "heading",
      "value": {"text": "Hello World", "size": "h2"},
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

### Block value types

| Block type | Value format |
|-----------|-------------|
| `CharBlock` | String |
| `TextBlock` | String |
| `RichTextBlock` | HTML string (format depends on output setting) |
| `IntegerBlock` | Integer |
| `FloatBlock` | Float |
| `BooleanBlock` | Boolean |
| `DateBlock` | ISO date string |
| `DateTimeBlock` | ISO datetime string |
| `URLBlock` | URL string |
| `EmailBlock` | Email string |
| `ChoiceBlock` | Selected choice value |
| `ImageChooserBlock` | Image ID (integer) |
| `PageChooserBlock` | Page ID (integer) |
| `DocumentChooserBlock` | Document ID (integer) |
| `StructBlock` | Object with named fields |
| `ListBlock` | Array of values |
| `StreamBlock` | Array of blocks (nested) |

## Writing StreamField data

Send the same format back. Each block needs `type` and `value`. The `id` field is optional on create but should be preserved on updates to maintain block identity.

```json
{
  "body": [
    {
      "type": "heading",
      "value": {"text": "New Heading", "size": "h3"},
      "id": "a1b2c3d4"
    },
    {
      "type": "paragraph",
      "value": "<p>Updated paragraph</p>",
      "id": "e5f6g7h8"
    }
  ]
}
```

### Generating block IDs

When adding new blocks, generate a UUID v4 string for the `id` field:

```python
import uuid
block_id = str(uuid.uuid4())
```

```javascript
const blockId = crypto.randomUUID();
```

### RichTextBlock values

`RichTextBlock` values inside StreamField accept the same format options as top-level [RichTextField](rich-text.md) values. You can send:

- A plain HTML string (default): `"value": "<p>Hello <strong>world</strong></p>"`
- A format dict with markdown: `"value": {"format": "markdown", "content": "Hello **world**"}`
- A format dict with HTML: `"value": {"format": "html", "content": "<p>Hello</p>"}`

This is especially useful when combined with `?rich_text_format=markdown` for reading: fetch content as markdown, let users edit the markdown, then send it back with the format wrapper — no client-side markdown-to-HTML conversion needed.

```json
{
  "type": "paragraph",
  "value": {"format": "markdown", "content": "Hello **world**"},
  "id": "e5f6g7h8"
}
```

The same conversion applies recursively inside StructBlocks — if a StructBlock contains a RichTextBlock child, you can use the format dict for that child's value too.

## StructBlock

StructBlock values are objects whose keys match the child block names:

```json
{
  "type": "heading",
  "value": {
    "text": "Hello World",
    "size": "h2"
  },
  "id": "abc123"
}
```

The keys and types depend on the block definition in your Wagtail model. Use the [Schema Discovery API](../api/schema-discovery.md) to inspect the expected structure — the `streamfield_blocks` section of the schema response lists every block type, its value schema, and nested StructBlock/ListBlock definitions.

## ListBlock

ListBlock values are arrays:

```json
{
  "type": "gallery",
  "value": [
    {"image": 42, "caption": "First photo"},
    {"image": 43, "caption": "Second photo"}
  ],
  "id": "def456"
}
```

## Round-trip editing

The API is designed for round-trip fidelity: read a page, modify some fields, write it back, and no data is lost. This is verified by the test suite.

```bash
# 1. Read
BODY=$(curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/5/ | jq '.body')

# 2. Modify (e.g., add a block)
NEW_BODY=$(echo $BODY | jq '. + [{"type":"paragraph","value":"<p>New block</p>","id":"new-uuid"}]')

# 3. Write back
curl -X PATCH \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"body\": $NEW_BODY}" \
     http://localhost:8000/api/write/v1/pages/5/
```

!!! warning "Preserve block IDs"
    When updating a StreamField, always preserve the `id` of existing blocks. Wagtail uses these UUIDs to track block identity across revisions. Changing them may cause issues with revision diffs in the Wagtail admin.
