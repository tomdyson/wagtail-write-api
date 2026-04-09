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

### Per-request: `?rich_text_format=markdown`

Add `?rich_text_format=markdown` to any page detail request to get rich text fields as Markdown instead of HTML:

```bash
# Default (HTML)
GET /pages/4/
{"body": "<p>Hello <strong>world</strong></p>"}

# Markdown
GET /pages/4/?rich_text_format=markdown
{"body": "Hello **world**"}
```

This applies to both `RichTextField` values and `RichTextBlock` values inside StreamFields. The conversion uses `markdownify` on the server, so no client-side HTML parsing is needed.

**Round-trip workflow:** Read with `?rich_text_format=markdown`, edit the Markdown, write back with `{"format": "markdown", "content": "..."}`. Bold, italic, headings, links, and lists survive the round trip. See the note below about Wagtail internal links.

### Site-wide: `RICH_TEXT_OUTPUT_FORMAT` setting

To change the default output format for all responses, use the `RICH_TEXT_OUTPUT_FORMAT` setting:

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

The `?rich_text_format` query parameter overrides this setting on a per-request basis.

!!! tip "For CMS editors"
    If your client needs to read content, edit it, and write it back, use `"wagtail"` format or the `?rich_text_format=markdown` parameter. With the default `"html"` format, Wagtail internal links are expanded to URL paths, which can't be losslessly converted back to page IDs.

!!! warning "Wagtail internal links and markdown round-trips"
    Wagtail stores internal links as `<a linktype="page" id="5">`. When reading as markdown, these are expanded to standard URL links (e.g. `[text](/about/)`). Writing back as markdown creates a regular `<a href>` — the page ID reference is lost. If preserving internal link references matters, use `wagtail://` links in your markdown input: `[text](wagtail://page/5)`.

## StreamField blocks sent to a RichTextField

If a client accidentally sends StreamField-style blocks (a list of `{"type": ..., "value": ...}` dicts) to a `RichTextField`, the API extracts the HTML content from the blocks rather than storing a stringified list. Paragraph and text block values are concatenated, and heading blocks are converted to HTML heading tags.

This is a convenience fallback — for best results, send one of the documented input formats above.

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
