from ninja.security import HttpBearer

from wagtail_write_api.models import ApiToken


class WagtailTokenAuth(HttpBearer):
    def authenticate(self, request, token: str):
        try:
            token_obj = ApiToken.objects.select_related("user").get(key=token)
        except ApiToken.DoesNotExist:
            return None

        if not token_obj.user.is_active:
            return None

        request.user = token_obj.user
        return token_obj.user
