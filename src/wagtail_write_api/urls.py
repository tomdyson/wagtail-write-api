from django.urls import path

from wagtail_write_api.api import api

urlpatterns = [
    path("", api.urls),
]
