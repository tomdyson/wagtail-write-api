# Mobile app

wagtail-write-api includes a Wagtail admin page that generates a QR code for connecting the [Wagtail Mobile](https://github.com/tomdyson/wagtail-mobile) app. This lets users connect their phone to the CMS without manually typing URLs or credentials.

## How it works

1. Open your Wagtail admin and click **Mobile app** in the sidebar
2. A QR code is displayed containing your API URL and token
3. In the Wagtail Mobile app, tap **Scan QR Code** on the login screen
4. Point your phone's camera at the QR code — you're connected

The QR code encodes a JSON payload:

```json
{"url": "https://example.com/api/write/v1", "token": "your-api-token"}
```

## API URL detection

The admin view auto-detects your API base URL by reversing the token endpoint URL from your Django URL configuration. The detected URL is shown below the QR code so you can verify it's correct.

If your site is behind a reverse proxy, make sure Django's `ALLOWED_HOSTS` and proxy headers are configured so that `request.build_absolute_uri()` returns the correct public URL.

## Security

The QR code contains a bearer token with the same permissions as the logged-in admin user. Treat it like a password:

- Don't screenshot and share it
- Don't display it on a projector in a meeting
- Each admin user gets their own token — the QR code is unique per user
- Tokens can be reset with `python manage.py create_api_token --reset <username>`
