from django.contrib.auth import authenticate
from ninja import Router, Schema

from wagtail_write_api.models import ApiToken

router = Router(tags=["auth"])


class TokenRequest(Schema):
    username: str
    password: str


class TokenResponse(Schema):
    token: str
    username: str


@router.post("/token/", response={200: TokenResponse, 401: dict}, url_name="obtain_token")
def obtain_token(request, payload: TokenRequest):
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None or not user.is_active:
        return 401, {
            "error": "authentication_failed",
            "message": "Invalid username or password",
        }
    token, _ = ApiToken.objects.get_or_create(user=user)
    return {"token": token.key, "username": user.get_username()}
