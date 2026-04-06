# Installation

## Requirements

- Python 3.10 or later
- Wagtail 6.0 or later
- Django REST Framework (for token authentication)

## Install the package

=== "pip"

    ```bash
    pip install wagtail-write-api
    ```

=== "uv"

    ```bash
    uv add wagtail-write-api
    ```

=== "Poetry"

    ```bash
    poetry add wagtail-write-api
    ```

## Dependencies

The following packages are installed automatically:

| Package | Purpose |
|---------|---------|
| `django-ninja` | API framework (Pydantic + OpenAPI) |
| `djangorestframework` | Token authentication |
| `markdown` | Markdown to HTML conversion |
| `markdownify` | HTML to Markdown conversion |

## Configure Django

Add the required apps to `INSTALLED_APPS`:

```python title="settings.py"
INSTALLED_APPS = [
    # ... your existing apps ...

    # Required for token auth
    "rest_framework",
    "rest_framework.authtoken",

    # The write API
    "wagtail_write_api",
]
```

Run migrations to create the token auth tables:

```bash
python manage.py migrate
```

## Add the URL routes

Include the API URLs in your project's URL configuration:

```python title="urls.py"
from django.urls import include, path

urlpatterns = [
    path("api/write/v1/", include("wagtail_write_api.urls")),
    # ... your other URL patterns ...
]
```

## Create an API token

Generate a token for a user:

```bash
python manage.py drf_create_token admin
```

This prints a token you can use in the `Authorization` header:

```
Generated token: 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

## Verify it works

Start the dev server and check the interactive docs:

```bash
python manage.py runserver
```

Open [http://localhost:8000/api/write/v1/docs](http://localhost:8000/api/write/v1/docs) in your browser.

Test with curl:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/write/v1/pages/
```
