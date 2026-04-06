# Example App

The `example/` directory contains a complete Wagtail project used for both development and testing. It includes deliberately complex page models that exercise every feature of the API.

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
python manage.py migrate
python manage.py seed_demo
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
