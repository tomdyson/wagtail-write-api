from django.utils.text import slugify


def generate_unique_slug(title: str, parent_page) -> str:
    """Generate a slug from title, ensuring uniqueness among siblings."""
    base_slug = slugify(title)
    if not base_slug:
        base_slug = "page"

    slug = base_slug
    suffix = 1
    sibling_slugs = set(parent_page.get_children().values_list("slug", flat=True))
    while slug in sibling_slugs:
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


def resolve_page_type(type_str: str):
    """Resolve 'app_label.ModelName' to a Django model class."""
    from django.apps import apps

    try:
        app_label, model_name = type_str.rsplit(".", 1)
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return None
