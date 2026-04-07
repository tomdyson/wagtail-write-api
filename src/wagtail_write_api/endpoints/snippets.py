import json
from typing import Optional

from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from ninja import Router
from ninja.errors import HttpError

from wagtail_write_api.auth import WagtailTokenAuth
from wagtail_write_api.settings import api_settings

router = Router(tags=["snippets"], auth=WagtailTokenAuth())


def _resolve_snippet_model(type_str: str):
    """Resolve 'app_label.ModelName' to a registered snippet model class."""
    from django.apps import apps
    from wagtail.snippets.models import get_snippet_models

    try:
        app_label, model_name = type_str.rsplit(".", 1)
        model = apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return None

    if model not in get_snippet_models():
        return None
    return model


def _type_str_for(model_class):
    return f"{model_class._meta.app_label}.{model_class.__name__}"


def _serialize_snippet(instance, model_class, type_str):
    """Serialize a snippet instance using the snippet schema registry."""
    from wagtail_write_api.endpoints.pages import _serialize_value
    from wagtail_write_api.schema.registry import snippet_schema_registry

    data = {"id": instance.id, "meta": {"type": type_str}}

    try:
        read_schema, _, _ = snippet_schema_registry.get_schemas(type_str)
        for field_name in read_schema.model_fields:
            if field_name == "id":
                continue
            if hasattr(instance, field_name):
                val = getattr(instance, field_name)
                data[field_name] = _serialize_value(val)
    except KeyError:
        data["str"] = str(instance)

    return data


def _apply_snippet_fields(instance, body, model_class):
    """Apply request body fields to a snippet instance."""
    from wagtail.fields import RichTextField, StreamField

    from wagtail_write_api.converters.rich_text import convert_rich_text_input

    skip_keys = {"type", "id"}

    for key, value in body.items():
        if key in skip_keys:
            continue

        try:
            field = model_class._meta.get_field(key)
        except Exception:
            continue

        if isinstance(field, StreamField):
            setattr(instance, key, value)
        elif isinstance(field, RichTextField):
            setattr(instance, key, convert_rich_text_input(value))
        elif field.is_relation:
            setattr(instance, f"{key}_id", value)
        else:
            setattr(instance, key, value)


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------
@router.get("/")
def list_snippets(
    request,
    type: str,
    search: Optional[str] = None,
    offset: int = 0,
    limit: Optional[int] = None,
):
    model_class = _resolve_snippet_model(type)
    if not model_class:
        raise HttpError(422, f"Unknown or unregistered snippet type: {type}")

    if limit is None:
        limit = api_settings.DEFAULT_PAGE_SIZE
    limit = min(limit, api_settings.MAX_PAGE_SIZE)

    qs = model_class.objects.all().order_by("pk")

    if search:
        if hasattr(model_class, "name"):
            qs = qs.filter(name__icontains=search)
        elif hasattr(model_class, "title"):
            qs = qs.filter(title__icontains=search)

    total_count = qs.count()
    snippets = qs[offset : offset + limit]

    type_str = _type_str_for(model_class)
    return {
        "items": [_serialize_snippet(s, model_class, type_str) for s in snippets],
        "meta": {"total_count": total_count},
    }


# ---------------------------------------------------------------------------
# DETAIL
# ---------------------------------------------------------------------------
@router.get("/{snippet_id}/")
def get_snippet(request, snippet_id: int, type: str):
    model_class = _resolve_snippet_model(type)
    if not model_class:
        raise HttpError(422, f"Unknown or unregistered snippet type: {type}")

    try:
        instance = model_class.objects.get(id=snippet_id)
    except model_class.DoesNotExist:
        raise Http404("Snippet not found")

    return _serialize_snippet(instance, model_class, _type_str_for(model_class))


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
@router.post("/", response={201: dict, 422: dict})
def create_snippet(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return 422, {"error": "validation_error", "message": f"Invalid JSON: {exc}"}

    type_str = body.get("type")
    if not type_str:
        return 422, {"error": "validation_error", "message": "type is required"}

    model_class = _resolve_snippet_model(type_str)
    if not model_class:
        return 422, {"error": "validation_error", "message": f"Unknown or unregistered snippet type: {type_str}"}

    instance = model_class()
    _apply_snippet_fields(instance, body, model_class)

    # full_clean raises Django ValidationError → caught by global handler → 400
    instance.full_clean()

    try:
        with transaction.atomic():
            instance.save()
    except IntegrityError as exc:
        return 422, {"error": "validation_error", "message": f"Duplicate or constraint violation: {exc}"}

    return 201, _serialize_snippet(instance, model_class, _type_str_for(model_class))


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
@router.patch("/{snippet_id}/", response={200: dict, 422: dict})
def update_snippet(request, snippet_id: int, type: str):
    model_class = _resolve_snippet_model(type)
    if not model_class:
        return 422, {"error": "validation_error", "message": f"Unknown or unregistered snippet type: {type}"}

    try:
        instance = model_class.objects.get(id=snippet_id)
    except model_class.DoesNotExist:
        raise Http404("Snippet not found")

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return 422, {"error": "validation_error", "message": f"Invalid JSON: {exc}"}

    _apply_snippet_fields(instance, body, model_class)
    instance.full_clean()

    try:
        with transaction.atomic():
            instance.save()
    except IntegrityError as exc:
        return 422, {"error": "validation_error", "message": f"Duplicate or constraint violation: {exc}"}

    return _serialize_snippet(instance, model_class, _type_str_for(model_class))


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
@router.delete("/{snippet_id}/")
def delete_snippet(request, snippet_id: int, type: str):
    model_class = _resolve_snippet_model(type)
    if not model_class:
        raise HttpError(422, f"Unknown or unregistered snippet type: {type}")

    try:
        instance = model_class.objects.get(id=snippet_id)
    except model_class.DoesNotExist:
        raise Http404("Snippet not found")

    instance.delete()
    return HttpResponse(status=204)
