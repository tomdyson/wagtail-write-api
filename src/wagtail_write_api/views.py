import io
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

import qrcode
import qrcode.image.svg

from wagtail_write_api.models import ApiToken


@login_required
def qr_connect(request):
    token, _ = ApiToken.objects.get_or_create(user=request.user)

    # Auto-detect API base URL by reversing the auth endpoint
    try:
        auth_url = reverse("api-1.0.0:obtain_token")
        # Strip /auth/token/ suffix to get the API base path
        base_path = auth_url.rsplit("/auth/token/", 1)[0]
        if not base_path:
            base_path = "/"
        api_url = request.build_absolute_uri(base_path).rstrip("/")
    except Exception:
        api_url = request.build_absolute_uri("/").rstrip("/")

    payload = json.dumps({"url": api_url, "token": token.key})

    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(payload, image_factory=factory, box_size=12)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")

    return render(
        request,
        "wagtail_write_api/qr_connect.html",
        {
            "svg": svg,
            "api_url": api_url,
            "header_title": "Mobile app",
            "header_icon": "link",
        },
    )
