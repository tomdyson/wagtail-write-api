# Authentication

The API uses token-based authentication via Django Ninja's `HttpBearer` scheme, with tokens stored in wagtail-write-api's own `ApiToken` model.

## How it works

Every request must include a valid token in the `Authorization` header:

```
Authorization: Bearer YOUR_TOKEN_HERE
```

The API looks up the token, retrieves the associated user, and sets `request.user` for the duration of the request.

## Creating tokens

### Via management command

```bash
python manage.py create_api_token username
```

To replace an existing token:

```bash
python manage.py create_api_token username --reset
```

### Via Python

```python
from wagtail_write_api.models import ApiToken

token, created = ApiToken.objects.get_or_create(user=user)
print(token.key)
```

### Via API (username/password login)

`POST /auth/token/` exchanges a username and password for an API token. This endpoint does not require an existing token.

```bash
curl -X POST https://example.com/api/write/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'
```

```json
{"token": "25e620d83a9c4a591f5986b1b74bbd4b7365c4be", "username": "admin"}
```

If the user already has a token, the existing token is returned. If not, a new one is created.

| Status | Condition |
|--------|-----------|
| `200 OK` | Valid credentials — returns token |
| `401 Unauthorized` | Invalid username or password |
| `401 Unauthorized` | User account is inactive |
| `422 Unprocessable Entity` | Missing username or password field |

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
