from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from django.db import models
from wagtail.fields import RichTextField, StreamField

SKIP_FIELDS = {
    "id",
    "page_ptr",
    "page_ptr_id",
    "content_type",
    "content_type_id",
    "path",
    "depth",
    "numchild",
    "url_path",
    "translation_key",
    "locale",
    "locale_id",
    "draft_title",
    "live_revision",
    "live_revision_id",
    "latest_revision",
    "latest_revision_id",
    "live",
    "has_unpublished_changes",
    "first_published_at",
    "last_published_at",
    "go_live_at",
    "expire_at",
    "expired",
    "locked",
    "locked_at",
    "locked_by",
    "locked_by_id",
    "latest_revision_created_at",
    "search_description",
    "seo_title",
    "show_in_menus",
    "owner",
    "owner_id",
}


def map_django_field(field) -> tuple[Any, Any] | None:
    """Map a Django model field to a (python_type, default) tuple for Pydantic."""
    if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel, models.ManyToManyField)):
        return None

    if isinstance(field, StreamField):
        if _is_optional(field):
            return (Optional[list[dict]], None)
        return (list[dict], ...)

    if isinstance(field, RichTextField):
        if _is_optional(field):
            return (Optional[str], None)
        return (str, "" if getattr(field, "blank", False) else ...)

    field_map: dict[type, type] = {
        models.CharField: str,
        models.TextField: str,
        models.SlugField: str,
        models.IntegerField: int,
        models.PositiveIntegerField: int,
        models.SmallIntegerField: int,
        models.BigIntegerField: int,
        models.FloatField: float,
        models.DecimalField: Decimal,
        models.BooleanField: bool,
        models.NullBooleanField: bool,
        models.DateTimeField: datetime,
        models.DateField: date,
        models.URLField: str,
        models.EmailField: str,
        models.UUIDField: str,
        models.FileField: str,
        models.FilePathField: str,
    }

    for django_type, python_type in field_map.items():
        if isinstance(field, django_type):
            if _is_optional(field):
                return (Optional[python_type], None)
            if getattr(field, "blank", False) and python_type is str:
                return (python_type, "")
            if getattr(field, "has_default", lambda: False)():
                return (python_type, field.default)
            return (python_type, ...)

    if isinstance(field, models.ForeignKey):
        return (Optional[int], None)

    return None


def _is_optional(field) -> bool:
    return getattr(field, "null", False) or getattr(field, "blank", False)
