from ninja import Router

from wagtail_write_api.auth import WagtailTokenAuth

router = Router(tags=["schema"], auth=WagtailTokenAuth())


@router.get("/")
def list_page_types(request):
    from wagtail_write_api.schema.registry import schema_registry

    types = []
    for type_str in schema_registry.all_page_types():
        model_class = _resolve_model(type_str)
        if not model_class:
            continue

        allowed_parents = [
            f"{m._meta.app_label}.{m.__name__}" for m in model_class.allowed_parent_page_models()
        ]
        allowed_children = [
            f"{m._meta.app_label}.{m.__name__}" for m in model_class.allowed_subpage_models()
        ]
        read_schema, _, _ = schema_registry.get_schemas(type_str)
        fields_summary = list(read_schema.model_fields.keys())

        available_parents = _get_available_parents(model_class)

        types.append(
            {
                "type": type_str,
                "verbose_name": model_class._meta.verbose_name,
                "allowed_parent_types": allowed_parents,
                "allowed_subpage_types": allowed_children,
                "fields_summary": fields_summary,
                "available_parents": available_parents,
            }
        )

    return {"page_types": types}


@router.get("/{type_str}/")
def get_page_type_schema(request, type_str: str):
    from wagtail_write_api.schema.registry import schema_registry

    try:
        read_schema, create_schema, patch_schema = schema_registry.get_schemas(type_str)
    except KeyError:
        from django.http import Http404

        raise Http404(f"Unknown page type: {type_str}")

    model_class = _resolve_model(type_str)
    streamfield_meta = _get_streamfield_meta(model_class) if model_class else {}
    richtext_fields = _get_richtext_fields(model_class) if model_class else []

    return {
        "type": type_str,
        "create_schema": create_schema.model_json_schema(),
        "patch_schema": patch_schema.model_json_schema(),
        "read_schema": read_schema.model_json_schema(),
        "streamfield_blocks": streamfield_meta,
        "richtext_fields": richtext_fields,
    }


def _get_available_parents(model_class):
    """Return actual page instances that can serve as parents for this page type.

    Only populated when the page type has a real parent constraint (i.e.
    wagtailcore.Page is NOT among its allowed parents).  When Page is allowed,
    almost every page in the tree qualifies, so listing instances is noise
    rather than signal — return an empty list and let the client query if needed.
    """
    from wagtail.models import Page

    from wagtail_write_api.endpoints.pages import _get_url_path

    parent_models = model_class.allowed_parent_page_models()
    if Page in parent_models:
        return []

    result = []
    for parent_model in parent_models:
        type_str = f"{parent_model._meta.app_label}.{parent_model.__name__}"
        pages = parent_model.objects.all().order_by("path")[:10]
        for page in pages:
            result.append(
                {
                    "id": page.id,
                    "title": page.title,
                    "type": type_str,
                    "url_path": _get_url_path(page),
                }
            )
    return result


def _resolve_model(type_str):
    from django.apps import apps

    try:
        app_label, model_name = type_str.rsplit(".", 1)
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return None


def _get_richtext_fields(model_class):
    """Return a list of field names that are RichTextFields."""
    from wagtail.fields import RichTextField

    return [
        field.name
        for field in model_class._meta.get_fields()
        if isinstance(field, RichTextField)
    ]


def _get_streamfield_meta(model_class):
    """Introspect StreamField definitions and return block type schemas."""
    from wagtail.fields import StreamField

    result = {}
    for field in model_class._meta.get_fields():
        if isinstance(field, StreamField):
            stream_block = field.stream_block
            block_types = []
            for name, block in stream_block.child_blocks.items():
                block_types.append({"type": name, "schema": _describe_block(block)})
            result[field.name] = block_types
    return result


def _describe_block(block):
    """Produce a JSON-serializable schema description for a Wagtail block."""
    from wagtail.blocks import (
        BooleanBlock,
        CharBlock,
        ChoiceBlock,
        DateBlock,
        DateTimeBlock,
        EmailBlock,
        FloatBlock,
        IntegerBlock,
        ListBlock,
        PageChooserBlock,
        RichTextBlock,
        StreamBlock,
        StructBlock,
        TextBlock,
        URLBlock,
    )
    from wagtail.images.blocks import ImageChooserBlock

    if isinstance(block, StructBlock):
        properties = {}
        for child_name, child_block in block.child_blocks.items():
            child_schema = _describe_block(child_block)
            child_schema["required"] = getattr(child_block.meta, "required", True)
            properties[child_name] = child_schema
        return {"type": "object", "properties": properties}

    if isinstance(block, ListBlock):
        return {"type": "array", "items": _describe_block(block.child_block)}

    if isinstance(block, StreamBlock):
        block_types = []
        for name, child_block in block.child_blocks.items():
            block_types.append({"type": name, "schema": _describe_block(child_block)})
        return {"type": "streamfield", "block_types": block_types}

    if isinstance(block, ChoiceBlock):
        choices = [
            choice[0] for choice in block.field.choices if choice[0] not in (None, "")
        ]
        return {"type": "string", "enum": choices}

    if isinstance(block, RichTextBlock):
        return {"type": "richtext"}

    if isinstance(block, ImageChooserBlock):
        return {"type": "image_chooser"}

    if isinstance(block, PageChooserBlock):
        return {"type": "page_chooser"}

    if isinstance(block, BooleanBlock):
        return {"type": "boolean"}

    if isinstance(block, IntegerBlock):
        return {"type": "integer"}

    if isinstance(block, FloatBlock):
        return {"type": "float"}

    if isinstance(block, (DateTimeBlock,)):
        return {"type": "datetime"}

    if isinstance(block, (DateBlock,)):
        return {"type": "date"}

    if isinstance(block, URLBlock):
        return {"type": "url"}

    if isinstance(block, EmailBlock):
        return {"type": "email"}

    if isinstance(block, (CharBlock, TextBlock)):
        return {"type": "string"}

    # Fallback for unknown block types
    return {"type": block.__class__.__name__}
