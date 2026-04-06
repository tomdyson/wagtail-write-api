# Authentication

The API uses token-based authentication via Django REST Framework's `TokenAuthentication`, wrapped in Django Ninja's `HttpBearer` scheme.

## How it works

Every request must include a valid token in the `Authorization` header:

```
Authorization: Bearer YOUR_TOKEN_HERE
```

The API looks up the token in the `authtoken_token` table (provided by `rest_framework.authtoken`), retrieves the associated user, and sets `request.user` for the duration of the request.

## Creating tokens

### Via management command

```bash
python manage.py drf_create_token username
```

### Via Django admin

Tokens can be managed in the Django admin at `/django-admin/authtoken/tokenproxy/`.

### Via Python

```python
from rest_framework.authtoken.models import Token

token, created = Token.objects.get_or_create(user=user)
print(token.key)
```

## Error responses

| Status | Condition |
|--------|-----------|
| `401 Unauthorized` | Missing `Authorization` header |
| `401 Unauthorized` | Invalid token |
| `401 Unauthorized` | Token belongs to an inactive user |

## Permissions

Authentication tells the API *who you are*. What you can *do* is controlled by Wagtail's permission system. See the [Permissions guide](../guides/permissions.md) for details.

## Optional: unauthenticated reads

By default, all endpoints require authentication. To allow unauthenticated GET requests:

```python title="settings.py"
WAGTAIL_WRITE_API = {
    "REQUIRE_AUTH_FOR_READ": False,
}
```

Write operations always require authentication regardless of this setting.

## Future: custom auth backends

The authentication class can be replaced for projects that need JWT or OAuth2. This is planned for a future version.
