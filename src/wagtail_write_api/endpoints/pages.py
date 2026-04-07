import json
from typing import Optional

from django.http import Http404, HttpResponse
from ninja import Router

from wagtail_write_api.auth import WagtailTokenAuth
from wagtail_write_api.permissions import get_user_page_permissions
from wagtail_write_api.settings import api_settings
from wagtail_write_api.utils import generate_unique_slug, resolve_page_type

router = Router(tags=["pages"], auth=WagtailTokenAuth())


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------
@router.get("/")
def list_pages(
    request,
    type: Optional[str] = None,
    parent: Optional[str] = None,
    descendant_of: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    order: Optional[str] = None,
    offset: int = 0,
    limit: Optional[int] = None,
    slug: Optional[str] = None,
    path: Optional[str] = None,
):
    from wagtail.models import Page

    if limit is None:
        limit = api_settings.DEFAULT_PAGE_SIZE
    limit = min(limit, api_settings.MAX_PAGE_SIZE)

    qs = Page.objects.all().order_by("path")

    if type:
        model_class = resolve_page_type(type)
        if model_class:
            qs = model_class.objects.all().order_by("path")

    if parent:
        try:
            parent_page = Page.objects.get(id=int(parent))
        except (ValueError, Page.DoesNotExist):
            parent_page = _resolve_page_by_path(parent)
        if parent_page:
            qs = qs.child_of(parent_page)
        else:
            qs = qs.none()

    if descendant_of:
        try:
            ancestor = Page.objects.get(id=int(descendant_of))
        except (ValueError, Page.DoesNotExist):
            ancestor = _resolve_page_by_path(descendant_of)
        if ancestor:
            qs = qs.descendant_of(ancestor)
        else:
            qs = qs.none()

    if status == "live":
        qs = qs.filter(live=True, has_unpublished_changes=False)
    elif status == "draft":
        qs = qs.filter(live=False)
    elif status == "live+draft":
        qs = qs.filter(live=True, has_unpublished_changes=True)

    if slug:
        qs = qs.filter(slug=slug)

    if path:
        resolved = _resolve_page_by_path(path)
        if resolved:
            qs = qs.filter(id=resolved.id)
        else:
            qs = qs.none()

    if search:
        qs = qs.search(search)

    if order:
        order_fields = [f.strip() for f in order.split(",")]
        qs = qs.order_by(*order_fields)

    total_count = qs.count()
    pages = qs[offset : offset + limit]

    items = []
    for page in pages:
        specific = page.specific
        type_str = f"{specific._meta.app_label}.{specific.__class__.__name__}"
        items.append(
            {
                "id": page.id,
                "title": page.title,
                "slug": page.slug,
                "meta": {
                    "type": type_str,
                    "live": page.live,
                    "has_unpublished_changes": page.has_unpublished_changes,
                    "parent_id": page.get_parent().id if page.get_parent() else None,
                    "url_path": _get_url_path(page),
                },
            }
        )

    return {"items": items, "meta": {"total_count": total_count}}


# ---------------------------------------------------------------------------
# DETAIL
# ---------------------------------------------------------------------------
@router.get("/{page_id}/")
def get_page(request, page_id: int, version: Optional[str] = None):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id)
    except Page.DoesNotExist:
        raise Http404("Page not found")

    specific = page.specific
    type_str = f"{specific._meta.app_label}.{specific.__class__.__name__}"

    # Draft-aware reads
    if version == "live":
        live_rev = specific.live_revision
        source = live_rev.as_object() if live_rev else specific
    elif specific.has_unpublished_changes and specific.get_latest_revision():
        source = specific.get_latest_revision().as_object()
    else:
        source = specific

    data = _serialize_page(source, specific, type_str, request.user)
    return data


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
@router.post("/", response={201: dict, 422: dict})
def create_page(request):
    from wagtail.models import Page

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return 422, {"error": "validation_error", "message": f"Invalid JSON: {exc}"}
    type_str = body.get("type")
    parent_ref = body.get("parent")

    if not type_str or not parent_ref:
        return 422, {"error": "validation_error", "message": "type and parent are required"}

    model_class = resolve_page_type(type_str)
    if not model_class:
        return 422, {"error": "validation_error", "message": f"Unknown page type: {type_str}"}

    if isinstance(parent_ref, str):
        parent_ref = parent_ref.strip()
        if not parent_ref:
            return 422, {
                "error": "validation_error",
                "message": "type and parent are required",
            }
    # Resolve parent — accepts an integer ID or a URL path string
    if isinstance(parent_ref, str) and not parent_ref.isdigit():
        parent_page = _resolve_page_by_path(parent_ref)
        if not parent_page:
            return 422, {
                "error": "validation_error",
                "message": f"No page found at path: {parent_ref}",
            }
        parent_page = parent_page.specific
    else:
        parent_id = int(parent_ref)
        try:
            parent_page = Page.objects.get(id=parent_id).specific
        except Page.DoesNotExist:
            return 422, {
                "error": "validation_error",
                "message": f"Parent page {parent_id} not found",
            }

    # Check parent allows this child type
    allowed = parent_page.specific_class.allowed_subpage_models()
    if model_class not in allowed:
        return 422, {
            "error": "validation_error",
            "message": f"{type_str} cannot be created under {parent_page.specific_class.__name__}",
        }

    # Build the page instance
    slug = body.get("slug") or generate_unique_slug(body.get("title", "page"), parent_page)
    page = model_class(
        title=body.get("title", ""),
        slug=slug,
        live=False,
        owner=request.user,
    )

    # Apply additional fields
    try:
        _apply_fields(page, body, model_class)
    except (TypeError, ValueError, AttributeError) as exc:
        return 422, {"error": "validation_error", "message": f"Invalid field data: {exc}"}

    # Validate before saving — full_clean() produces field-level errors
    page.full_clean(exclude=["path", "depth"])

    # Add to tree and save revision
    try:
        parent_page.add_child(instance=page)
    except (TypeError, ValueError) as exc:
        return 422, {"error": "validation_error", "message": f"Failed to create page: {exc}"}

    revision = page.save_revision(user=request.user)

    # Optionally publish
    if body.get("action") == "publish":
        revision.publish(user=request.user)
        page.refresh_from_db()

    type_str_actual = f"{page._meta.app_label}.{page.__class__.__name__}"
    data = _serialize_page(page, page, type_str_actual, request.user)
    return 201, data


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
@router.patch("/{page_id}/", response={200: dict, 404: dict, 422: dict})
def update_page(request, page_id: int):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id).specific
    except Page.DoesNotExist:
        raise Http404("Page not found")

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return 422, {"error": "validation_error", "message": f"Invalid JSON: {exc}"}

    # Apply fields
    if "title" in body:
        page.title = body["title"]
    if "slug" in body:
        page.slug = body["slug"]

    try:
        _apply_fields(page, body, page.__class__)
    except (TypeError, ValueError, AttributeError) as exc:
        return 422, {"error": "validation_error", "message": f"Invalid field data: {exc}"}

    page.save()
    revision = page.save_revision(user=request.user)

    if body.get("action") == "publish":
        revision.publish(user=request.user)
        page.refresh_from_db()

    type_str = f"{page._meta.app_label}.{page.__class__.__name__}"
    data = _serialize_page(page, page, type_str, request.user)
    return data


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
@router.delete("/{page_id}/")
def delete_page(request, page_id: int):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id)
    except Page.DoesNotExist:
        raise Http404("Page not found")

    page.delete()
    return HttpResponse(status=204)


# ---------------------------------------------------------------------------
# PUBLISH
# ---------------------------------------------------------------------------
@router.post("/{page_id}/publish/")
def publish_page(request, page_id: int):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id).specific
    except Page.DoesNotExist:
        raise Http404("Page not found")

    revision = page.get_latest_revision()
    if revision:
        revision.publish(user=request.user)
    else:
        page.live = True
        page.save()

    page.refresh_from_db()
    type_str = f"{page._meta.app_label}.{page.__class__.__name__}"
    return _serialize_page(page, page, type_str, request.user)


# ---------------------------------------------------------------------------
# UNPUBLISH
# ---------------------------------------------------------------------------
@router.post("/{page_id}/unpublish/")
def unpublish_page(request, page_id: int):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id).specific
    except Page.DoesNotExist:
        raise Http404("Page not found")

    page.unpublish(user=request.user)
    page.refresh_from_db()
    type_str = f"{page._meta.app_label}.{page.__class__.__name__}"
    return _serialize_page(page, page, type_str, request.user)


# ---------------------------------------------------------------------------
# REVISIONS
# ---------------------------------------------------------------------------
@router.get("/{page_id}/revisions/")
def list_revisions(request, page_id: int):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id)
    except Page.DoesNotExist:
        raise Http404("Page not found")

    revisions = page.revisions.order_by("-created_at")
    items = [
        {
            "id": rev.id,
            "created_at": rev.created_at.isoformat(),
            "user": rev.user.username if rev.user else None,
        }
        for rev in revisions
    ]
    return {"items": items}


@router.get("/{page_id}/revisions/{revision_id}/")
def get_revision(request, page_id: int, revision_id: int):
    from wagtail.models import Page, Revision

    try:
        page = Page.objects.get(id=page_id)
    except Page.DoesNotExist:
        raise Http404("Page not found")

    try:
        revision = page.revisions.get(id=revision_id)
    except Revision.DoesNotExist:
        raise Http404("Revision not found")

    rev_page = revision.as_object()
    type_str = f"{page.specific._meta.app_label}.{page.specific.__class__.__name__}"
    return _serialize_page(rev_page, page.specific, type_str, request.user)


# ---------------------------------------------------------------------------
# COPY
# ---------------------------------------------------------------------------
@router.post("/{page_id}/copy/", response={201: dict})
def copy_page(request, page_id: int):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id).specific
    except Page.DoesNotExist:
        raise Http404("Page not found")

    body = json.loads(request.body)
    dest_id = body.get("destination")
    recursive = body.get("recursive", True)

    try:
        destination = Page.objects.get(id=dest_id)
    except Page.DoesNotExist:
        raise Http404("Destination page not found")

    # Generate a unique slug for the copy
    new_slug = generate_unique_slug(page.title, destination)
    new_page = page.copy(
        to=destination,
        recursive=recursive,
        keep_live=False,
        user=request.user,
        update_attrs={"slug": new_slug},
    )

    type_str = f"{new_page._meta.app_label}.{new_page.__class__.__name__}"
    data = _serialize_page(new_page, new_page, type_str, request.user)
    return 201, data


# ---------------------------------------------------------------------------
# MOVE
# ---------------------------------------------------------------------------
@router.post("/{page_id}/move/")
def move_page(request, page_id: int):
    from wagtail.models import Page

    try:
        page = Page.objects.get(id=page_id)
    except Page.DoesNotExist:
        raise Http404("Page not found")

    body = json.loads(request.body)
    dest_id = body.get("destination")
    position = body.get("position", "last-child")

    try:
        destination = Page.objects.get(id=dest_id)
    except Page.DoesNotExist:
        raise Http404("Destination page not found")

    page.move(destination, pos=position)
    page.refresh_from_db()
    specific = page.specific
    type_str = f"{specific._meta.app_label}.{specific.__class__.__name__}"
    return _serialize_page(specific, specific, type_str, request.user)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_page_by_path(path: str):
    """Resolve a URL path like '/blog/' to a Page, using the default Site's routing."""
    from wagtail.models import Site

    # Normalise: ensure leading and trailing slashes
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path = path + "/"

    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        return None

    try:
        page, _, _ = site.root_page.specific.route(None, [c for c in path.split("/") if c])
        return page
    except Exception:
        return None


def _get_url_path(page):
    """Return the site-relative URL path for a page (e.g. '/blog/my-post/')."""
    from wagtail.models import Site

    site = Site.objects.filter(is_default_site=True).first()
    if not site or not page.url_path:
        return None

    root_path = site.root_page.url_path.rstrip("/")
    url_path = page.url_path
    if url_path.startswith(root_path):
        url_path = url_path[len(root_path):]
    return url_path or "/"


def _apply_fields(page, body, model_class):
    """Apply request body fields to a page instance."""
    from modelcluster.fields import ParentalKey
    from wagtail.fields import RichTextField, StreamField
    from wagtail.models import Orderable

    from wagtail_write_api.converters.rich_text import convert_rich_text_input

    skip_keys = {"type", "parent", "title", "slug", "action", "id"}

    # Gather orderable relation names
    orderable_rels = {}
    for rel in model_class._meta.related_objects:
        if not hasattr(rel, "related_model"):
            continue
        if issubclass(rel.related_model, Orderable):
            orderable_rels[rel.get_accessor_name()] = rel.related_model

    for key, value in body.items():
        if key in skip_keys:
            continue

        # Handle orderable children
        if key in orderable_rels:
            related_model = orderable_rels[key]
            manager = getattr(page, key)
            # Clear existing — use set() or individual removal
            existing = list(manager.all())
            for obj in existing:
                manager.remove(obj)
            for i, child_data in enumerate(value):
                child = related_model(sort_order=i, **child_data)
                manager.add(child)
            continue

        # Handle regular fields
        field = None
        try:
            field = model_class._meta.get_field(key)
        except Exception:
            continue

        if isinstance(field, StreamField):
            setattr(page, key, value)
        elif isinstance(field, RichTextField):
            setattr(page, key, convert_rich_text_input(value))
        elif field and field.is_relation:
            setattr(page, f"{key}_id", value)
        else:
            setattr(page, key, value)


def _serialize_page(source, page, type_str, user):
    """Serialize a page instance to a dict."""
    from wagtail_write_api.schema.registry import schema_registry

    data = {"id": page.id}

    try:
        read_schema, _, _ = schema_registry.get_schemas(type_str)
        for field_name in read_schema.model_fields:
            if field_name in ("id",):
                continue
            if hasattr(source, field_name):
                val = getattr(source, field_name)
                data[field_name] = _serialize_value(val)
    except KeyError:
        data["title"] = source.title
        data["slug"] = source.slug

    parent = page.get_parent()
    parent_specific = parent.specific if parent else None
    data["meta"] = {
        "type": type_str,
        "live": page.live,
        "has_unpublished_changes": page.has_unpublished_changes,
        "first_published_at": (
            page.first_published_at.isoformat() if page.first_published_at else None
        ),
        "last_published_at": (
            page.last_published_at.isoformat() if page.last_published_at else None
        ),
        "url_path": _get_url_path(page),
        "parent_id": parent.id if parent else None,
        "parent_type": (
            f"{parent_specific._meta.app_label}.{parent_specific.__class__.__name__}"
            if parent_specific
            else None
        ),
        "children_count": page.get_children().count(),
        "user_permissions": get_user_page_permissions(user, page),
    }

    data["hints"] = _build_hints(page, type_str)

    return data


def _build_hints(page, type_str):
    """Build actionable hints for LLM/CLI consumers."""
    hints = {}

    if not page.live:
        hints["publish"] = f"wagapi pages publish {page.id}"
    elif page.has_unpublished_changes:
        hints["publish"] = f"wagapi pages publish {page.id}"

    if page.live:
        hints["unpublish"] = f"wagapi pages unpublish {page.id}"

    hints["edit"] = f"wagapi pages update {page.id} --title '...' --body '...'"
    hints["view"] = f"wagapi pages get {page.id}"
    hints["delete"] = f"wagapi pages delete {page.id}"

    return hints


def _serialize_value(val):
    """Convert a field value to JSON-serializable form."""
    from datetime import date, datetime

    from wagtail.rich_text import RichText

    if val is None:
        return None
    if isinstance(val, RichText):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, (str, int, float, bool)):
        return val

    # StreamField value
    if hasattr(val, "stream_data"):
        try:
            return list(val.stream_data)
        except Exception:
            pass
    if hasattr(val, "stream_block"):
        result = []
        for block in val:
            result.append(
                {
                    "type": block.block_type,
                    "value": _serialize_block_value(block.value),
                    "id": block.id,
                }
            )
        return result

    # RelatedManager (e.g., Orderable children)
    if hasattr(val, "all"):
        from modelcluster.fields import ParentalKey

        items = []
        for obj in val.all():
            item = {}
            for field in obj._meta.get_fields():
                if isinstance(field, ParentalKey):
                    continue
                if field.name == "id":
                    item["id"] = obj.id
                elif hasattr(obj, field.name) and not field.is_relation:
                    item[field.name] = getattr(obj, field.name)
            items.append(item)
        return items

    # FK — return the ID
    if hasattr(val, "pk"):
        return val.pk

    try:
        return str(val)
    except Exception:
        return repr(val)


def _serialize_block_value(val):
    """Serialize a StreamField block value."""
    from wagtail.rich_text import RichText

    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, RichText):
        return str(val)
    if isinstance(val, dict):
        return {k: _serialize_block_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize_block_value(item) for item in val]
    if hasattr(val, "pk"):
        return val.pk
    return str(val)
