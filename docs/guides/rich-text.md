# Rich Text

Rich text fields (`RichTextField` and `RichTextBlock` in StreamField) accept input in three formats and output in a configurable format.

## Input formats

When writing to a rich text field, send an object with `format` and `content`:

=== "HTML"

    ```json
    {
      "body": {
        "format": "html",
        "content": "<p>Hello <strong>world</strong></p>"
      }
    }
    ```

=== "Markdown"

    ```json
    {
      "body": {
        "format": "markdown",
        "content": "Hello **world**"
      }
    }
    ```

=== "Wagtail internal"

    ```json
    {
      "body": {
        "format": "wagtail",
        "content": "<p>Link to <a linktype=\"page\" id=\"5\">about</a></p>"
      }
    }
    ```

=== "Plain string"

    ```json
    {
      "body": "<p>Also accepted as a plain string</p>"
    }
    ```

    Plain strings are treated as HTML and stored as-is.

## Linking to Wagtail pages from Markdown

Wagtail stores internal links using a special format: `<a linktype="page" id="5">`. To create these links from Markdown, use the `wagtail://` URL scheme:

```markdown
Check out [our about page](wagtail://page/5) for more info.
```

This is converted to Wagtail's internal link format on save:

```html
<p>Check out <a linktype="page" id="5">our about page</a> for more info.</p>
```

### Supported link types

| Syntax | Wagtail internal |
|--------|-----------------|
| `[text](wagtail://page/5)` | `<a linktype="page" id="5">text</a>` |
| `[text](wagtail://document/12)` | `<a linktype="document" id="12">text</a>` |
| `[text](wagtail://image/8)` | `<a linktype="image" id="8">text</a>` |

Standard Markdown links (`[text](https://example.com)`) are preserved as regular `<a href>` tags.

## Output format

The format used in GET responses is controlled by the `RICH_TEXT_OUTPUT_FORMAT` setting:

```python title="settings.py"
WAGTAIL_WRITE_API = {
    "RICH_TEXT_OUTPUT_FORMAT": "html",  # default
}
```

| Format | Use case | Example output |
|--------|----------|---------------|
| `"html"` | Display clients, simple editors | `<p>Link to <a href="/about/">about</a></p>` |
| `"wagtail"` | Round-trip editing, CMS editors | `<p>Link to <a linktype="page" id="5">about</a></p>` |
| `"markdown"` | Markdown-native clients | `Link to [about](/about/)` |

!!! tip "For CMS editors"
    If your client needs to read content, edit it, and write it back, use `"wagtail"` format. This preserves the internal link references (page IDs) through the round trip. With `"html"` format, internal links are expanded to URL paths, which can't be losslessly converted back.

## Rich text in StreamField

`RichTextBlock` values in StreamField accept the same input format:

```json
{
  "body": [
    {
      "type": "paragraph",
      "value": {
        "format": "markdown",
        "content": "A paragraph with **bold** text"
      },
      "id": "abc123"
    }
  ]
}
```
