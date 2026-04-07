from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from ninja import NinjaAPI

from wagtail_write_api.settings import api_settings

api = NinjaAPI(
    title="Wagtail Write API",
    version="1.0.0",
    docs_url=api_settings.DOCS_URL,
)


@api.exception_handler(PermissionDenied)
def on_permission_denied(request, exc):
    return api.create_response(
        request,
        {"error": "permission_denied", "message": str(exc) or "Permission denied"},
        status=403,
    )


@api.exception_handler(ValidationError)
def on_validation_error(request, exc):
    if hasattr(exc, "message_dict"):
        details = [
            {"field": field, "message": msgs[0] if len(msgs) == 1 else msgs}
            for field, msgs in exc.message_dict.items()
        ]
    else:
        details = [
            {"message": m.message % m.params if m.params else m.message}
            for m in exc.error_list
        ]
    return api.create_response(
        request,
        {"error": "validation_error", "message": "Validation failed", "details": details},
        status=400,
    )


@api.exception_handler(Exception)
def on_unhandled_error(request, exc):
    import logging

    logger = logging.getLogger("wagtail_write_api")
    logger.exception("Unhandled error in wagtail-write-api")
    return api.create_response(
        request,
        {"error": "server_error", "message": str(exc)},
        status=500,
    )


from wagtail_write_api.endpoints.images import router as images_router
from wagtail_write_api.endpoints.pages import router as pages_router
from wagtail_write_api.endpoints.schema_discovery import router as schema_router

api.add_router("/pages/", pages_router)
api.add_router("/images/", images_router)
api.add_router("/schema/", schema_router)
