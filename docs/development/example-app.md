# Example App

The `example/` directory contains a complete Wagtail project used for both development and testing. It includes deliberately complex page models that exercise every feature of the API.

## Running the example app

```bash
cd example
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

The `seed_demo` command prints API tokens for each user. Save the admin token for use in the examples below:

```bash
export TOKEN=<paste the admin token here>
```

The API docs are at [http://localhost:8000/api/write/v1/docs](http://localhost:8000/api/write/v1/docs).

## Trying the API

These examples use the seeded data. Page IDs may vary — check the list response to find the correct IDs in your instance.

### List all pages

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/ | python -m json.tool
```

### List blog posts only

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/api/write/v1/pages/?type=testapp.BlogPage" | python -m json.tool
```

### Get a page detail

Use an `id` from the list response (e.g. a blog post):

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/6/ | python -m json.tool
```

### Create a new blog post

The blog index page is the required parent for blog posts. Find its `id` from the list response (it has `"type": "testapp.BlogIndexPage"`), then:

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "type": "testapp.BlogPage",
       "parent": 5,
       "title": "My API Post",
       "published_date": "2026-04-01",
       "body": [
         {
           "type": "heading",
           "value": {"text": "Hello from the API", "size": "h2"}
         },
         {
           "type": "paragraph",
           "value": "<p>This post was created via the write API.</p>"
         }
       ],
       "authors": [
         {"name": "API User", "role": "Writer"}
       ]
     }' \
     http://localhost:8000/api/write/v1/pages/ | python -m json.tool
```

The response returns the created page with `"live": false` — it's a draft by default.

### Create and publish in one step

Add `"action": "publish"` to the request body:

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "type": "testapp.SimplePage",
       "parent": 3,
       "title": "Contact Us",
       "body": {
         "format": "markdown",
         "content": "Email us at **hello@example.com**."
       },
       "action": "publish"
     }' \
     http://localhost:8000/api/write/v1/pages/ | python -m json.tool
```

### Update a page

PATCH sends only the fields you want to change:

```bash
curl -s -X PATCH \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Updated Blog Post Title", "action": "publish"}' \
     http://localhost:8000/api/write/v1/pages/6/ | python -m json.tool
```

### Publish / unpublish

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/6/publish/ | python -m json.tool

curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/6/unpublish/ | python -m json.tool
```

### Create an event page

Events live under the "Events" SimplePage. Find its `id` from the list response, then:

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "type": "testapp.EventPage",
       "parent": 11,
       "title": "Launch Party",
       "start_date": "2026-06-15T18:00:00Z",
       "location": "The Grand Hall",
       "body": [
         {
           "type": "text",
           "value": "<p>Join us for the launch!</p>"
         }
       ],
       "action": "publish"
     }' \
     http://localhost:8000/api/write/v1/pages/ | python -m json.tool
```

### Upload an image

```bash
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@photo.jpg" \
     -F "title=My Photo" \
     http://localhost:8000/api/write/v1/images/ | python -m json.tool
```

### Delete a page

```bash
curl -s -X DELETE \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/pages/6/
```

Returns `204 No Content` on success.

### Discover available page types

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/write/v1/schema/ | python -m json.tool
```

## Test models

### SimplePage

A minimal page with just a rich text body. Used as a baseline for testing.

```python
class SimplePage(Page):
    body = RichTextField(blank=True)
```

### BlogIndexPage

A parent-only page that demonstrates `subpage_types` constraints.

```python
class BlogIndexPage(Page):
    intro = RichTextField(blank=True)
    subpage_types = ["testapp.BlogPage"]
```

### BlogPage

The "kitchen sink" model. Tests most field types, StreamField with nested blocks, and Orderable children.

```python
class BlogPage(Page):
    published_date = models.DateField(null=True, blank=True)
    feed_image = models.ForeignKey("wagtailimages.Image", ...)
    body = StreamField([
        ("heading", StructBlock([
            ("text", CharBlock()),
            ("size", ChoiceBlock(choices=[("h2","H2"), ("h3","H3"), ("h4","H4")])),
        ])),
        ("paragraph", RichTextBlock()),
        ("image", ImageChooserBlock()),
        ("gallery", ListBlock(StructBlock([
            ("image", ImageChooserBlock()),
            ("caption", CharBlock(required=False)),
        ]))),
        ("related_pages", ListBlock(PageChooserBlock())),
    ])

    parent_page_types = ["testapp.BlogIndexPage"]
    subpage_types = []
```

### BlogPageAuthor

An Orderable child model, testing InlinePanel support.

```python
class BlogPageAuthor(Orderable):
    page = ParentalKey(BlogPage, related_name="authors")
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=100, blank=True)
```

### EventPage

Tests datetime fields and the `write_api_exclude` feature.

```python
class EventPage(Page):
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255)
    legacy_id = models.CharField(max_length=50, blank=True)

    write_api_exclude = ["legacy_id"]
```

## Seed command

The `seed_demo` management command creates a realistic test environment:

```bash
cd example
uv run python manage.py migrate
uv run python manage.py seed_demo
```

### What it creates

**Users:**

| Username | Role | Permissions |
|----------|------|-------------|
| `admin` | Superuser | Full access |
| `editor` | Blog editor | Add + change on blog section |
| `moderator` | Moderator | Add + change + publish on all pages |
| `reviewer` | Read-only | No write permissions |

All users have the password `password`.

**Page tree:**

```
Root
└── Home
    ├── About (SimplePage)
    ├── Blog (BlogIndexPage)
    │   ├── Blog Post 1 (BlogPage)
    │   ├── Blog Post 2 (BlogPage)
    │   ├── Blog Post 3 (BlogPage)
    │   ├── Blog Post 4 (BlogPage)
    │   └── Blog Post 5 (BlogPage)
    └── Events (SimplePage)
        ├── Event 1 (EventPage)
        ├── Event 2 (EventPage)
        └── Event 3 (EventPage)
```

**API tokens** are printed to stdout for each user:

```
--- API Tokens ---
  admin: 62a887fe...
  editor: 4fbeb9c8...
  moderator: 6c8b9634...
  reviewer: a2377491...
```
