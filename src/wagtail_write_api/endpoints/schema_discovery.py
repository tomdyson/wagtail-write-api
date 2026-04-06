from ninja import Router

from wagtail_write_api.auth import WagtailTokenAuth

router = Router(tags=["schema"], auth=WagtailTokenAuth())


@router.get("/page-types/")
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

        types.append(
            {
                "type": type_str,
                "verbose_name": model_class._meta.verbose_name,
                "allowed_parent_types": allowed_parents,
                "allowed_subpage_types": allowed_children,
                "fields_summary": fields_summary,
            }
        )

    return {"page_types": types}


@router.get("/page-types/{type_str}/")
def get_page_type_schema(request, type_str: str):
    from wagtail_write_api.schema.registry import schema_registry

    try:
        read_schema, create_schema, patch_schema = schema_registry.get_schemas(type_str)
    except KeyError:
        from django.http import Http404

        raise Http404(f"Unknown page type: {type_str}")

    return {
        "type": type_str,
        "create_schema": create_schema.model_json_schema(),
        "patch_schema": patch_schema.model_json_schema(),
        "read_schema": read_schema.model_json_schema(),
    }


def _resolve_model(type_str):
    from django.apps import apps

    try:
        app_label, model_name = type_str.rsplit(".", 1)
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return None
