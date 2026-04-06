import json
from typing import Optional

from django.http import Http404, HttpResponse
from ninja import File, Form, Router, UploadedFile

from wagtail_write_api.auth import WagtailTokenAuth
from wagtail_write_api.settings import api_settings

router = Router(tags=["images"], auth=WagtailTokenAuth())


def _get_image_model():
    from wagtail.images import get_image_model

    return get_image_model()


def _serialize_image(image):
    data = {
        "id": image.id,
        "title": image.title,
        "width": image.width,
        "height": image.height,
        "file_url": image.file.url if image.file else None,
        "created_at": image.created_at.isoformat() if image.created_at else None,
    }
    # Generate renditions
    renditions = {}
    for name, spec in api_settings.IMAGE_RENDITIONS.items():
        try:
            rendition = image.get_rendition(spec)
            renditions[name] = rendition.url
        except Exception:
            renditions[name] = None
    data["renditions"] = renditions
    return data


@router.get("/")
def list_images(
    request,
    search: Optional[str] = None,
    offset: int = 0,
    limit: Optional[int] = None,
):
    Image = _get_image_model()

    if limit is None:
        limit = api_settings.DEFAULT_PAGE_SIZE
    limit = min(limit, api_settings.MAX_PAGE_SIZE)

    qs = Image.objects.all().order_by("-created_at")

    if search:
        qs = qs.filter(title__icontains=search)

    total_count = qs.count()
    images = qs[offset : offset + limit]

    return {
        "items": [_serialize_image(img) for img in images],
        "meta": {"total_count": total_count},
    }


@router.get("/{image_id}/")
def get_image(request, image_id: int):
    Image = _get_image_model()
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")

    return _serialize_image(image)


@router.post("/", response={201: dict})
def upload_image(
    request,
    file: UploadedFile = File(...),
    title: str = Form(""),
):
    Image = _get_image_model()

    image = Image(
        title=title or file.name,
        file=file,
        uploaded_by_user=request.user,
    )
    image.save()

    return 201, _serialize_image(image)


@router.patch("/{image_id}/")
def update_image(request, image_id: int):
    Image = _get_image_model()
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")

    body = json.loads(request.body)
    if "title" in body:
        image.title = body["title"]
    image.save()

    return _serialize_image(image)


@router.delete("/{image_id}/")
def delete_image(request, image_id: int):
    Image = _get_image_model()
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")

    image.delete()
    return HttpResponse(status=204)
