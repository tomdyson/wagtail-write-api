from typing import Any, Optional, Union

from pydantic import create_model

from wagtail_write_api.schema.fields import SKIP_FIELDS, map_django_field


def generate_schemas_for_model(model_class, model_kind="page"):
    """
    Introspect a Wagtail model and produce ReadSchema, CreateSchema, PatchSchema.

    model_kind controls which extra fields are added:
      "page"    — type, parent (required), action (optional)
      "snippet" — type only
    """
    model_name = model_class.__name__
    exclude = set(getattr(model_class, "write_api_exclude", []))

    # Collect fields
    read_fields: dict[str, Any] = {}
    write_fields: dict[str, Any] = {}

    for field in model_class._meta.get_fields():
        name = field.name
        if name in SKIP_FIELDS or name in exclude:
            continue

        mapped = map_django_field(field)
        if mapped is None:
            continue

        python_type, default = mapped
        read_fields[name] = (python_type, default)
        write_fields[name] = (python_type, default)

    # Handle Orderable children (ParentalKey relationships)
    from modelcluster.fields import ParentalKey
    from wagtail.models import Orderable

    for rel in model_class._meta.related_objects:
        if not hasattr(rel, "related_model"):
            continue
        related_model = rel.related_model
        if not issubclass(related_model, Orderable):
            continue
        # Check it's a ParentalKey pointing to our model
        if not any(
            isinstance(f, ParentalKey) and f.related_model is model_class
            for f in related_model._meta.get_fields()
            if hasattr(f, "related_model")
        ):
            continue

        child_schema = _generate_orderable_schema(related_model, model_class)
        rel_name = rel.get_accessor_name()
        read_fields[rel_name] = (list[child_schema], [])
        write_fields[rel_name] = (list[child_schema], [])

    # ReadSchema: includes id and all fields
    read_fields["id"] = (int, ...)
    ReadSchema = create_model(f"{model_name}Read", **read_fields)

    # CreateSchema: type required; parent+action only for pages
    create_fields = {}
    create_fields["type"] = (str, ...)
    if model_kind == "page":
        create_fields["parent"] = (Union[int, str], ...)
        create_fields["action"] = (Optional[str], None)
    for name, (python_type, default) in write_fields.items():
        if name == "slug":
            create_fields[name] = (Optional[str], None)
        else:
            create_fields[name] = (python_type, default)
    CreateSchema = create_model(f"{model_name}Create", **create_fields)

    # PatchSchema: all fields optional
    patch_fields = {}
    if model_kind == "page":
        patch_fields["action"] = (Optional[str], None)
    for name, (python_type, _) in write_fields.items():
        # Make everything Optional with None default
        if hasattr(python_type, "__origin__"):
            # Already Optional or other generic
            patch_fields[name] = (Optional[python_type], None)
        else:
            patch_fields[name] = (Optional[python_type], None)
    PatchSchema = create_model(f"{model_name}Patch", **patch_fields)

    return ReadSchema, CreateSchema, PatchSchema


def _generate_orderable_schema(related_model, parent_model):
    """Generate a Pydantic schema for an Orderable child model."""
    from modelcluster.fields import ParentalKey

    fields: dict[str, Any] = {}
    fields["id"] = (Optional[int], None)

    for field in related_model._meta.get_fields():
        if isinstance(field, ParentalKey):
            continue
        if field.name in ("id", "sort_order"):
            continue
        if isinstance(field, (type(None),)):
            continue
        mapped = map_django_field(field)
        if mapped:
            fields[field.name] = mapped

    return create_model(f"{related_model.__name__}Schema", **fields)
