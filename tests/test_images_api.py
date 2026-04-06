import io
import json

import pytest
from PIL import Image as PILImage


def _create_test_image():
    """Create a minimal valid PNG image in memory."""
    img = PILImage.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    buf.name = "test_image.png"
    return buf


@pytest.mark.django_db
class TestImageUpload:
    def test_upload_image(self, api_client, auth_header):
        img = _create_test_image()
        response = api_client.post(
            "/api/write/v1/images/",
            data={"file": img, "title": "Test Image"},
            **auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Image"
        assert data["id"] is not None
        assert data["width"] == 100
        assert data["height"] == 100


@pytest.mark.django_db
class TestImageList:
    def test_list_images(self, api_client, auth_header):
        # Upload an image first
        img = _create_test_image()
        api_client.post(
            "/api/write/v1/images/",
            data={"file": img, "title": "Listed Image"},
            **auth_header,
        )

        response = api_client.get("/api/write/v1/images/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1


@pytest.mark.django_db
class TestImageDetail:
    def test_get_image(self, api_client, auth_header):
        img = _create_test_image()
        upload = api_client.post(
            "/api/write/v1/images/",
            data={"file": img, "title": "Detail Image"},
            **auth_header,
        )
        image_id = upload.json()["id"]

        response = api_client.get(f"/api/write/v1/images/{image_id}/", **auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Detail Image"


@pytest.mark.django_db
class TestImageUpdate:
    def test_update_image_title(self, api_client, auth_header):
        img = _create_test_image()
        upload = api_client.post(
            "/api/write/v1/images/",
            data={"file": img, "title": "Old Title"},
            **auth_header,
        )
        image_id = upload.json()["id"]

        response = api_client.patch(
            f"/api/write/v1/images/{image_id}/",
            data=json.dumps({"title": "New Title"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"


@pytest.mark.django_db
class TestImageDelete:
    def test_delete_image(self, api_client, auth_header):
        img = _create_test_image()
        upload = api_client.post(
            "/api/write/v1/images/",
            data={"file": img, "title": "Delete Me"},
            **auth_header,
        )
        image_id = upload.json()["id"]

        response = api_client.delete(f"/api/write/v1/images/{image_id}/", **auth_header)
        assert response.status_code == 204
