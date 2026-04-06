from ninja.security import HttpBearer
from rest_framework.authtoken.models import Token


class WagtailTokenAuth(HttpBearer):
    def authenticate(self, request, token: str):
        try:
            token_obj = Token.objects.select_related("user").get(key=token)
        except Token.DoesNotExist:
            return None

        if not token_obj.user.is_active:
            return None

        request.user = token_obj.user
        return token_obj.user
