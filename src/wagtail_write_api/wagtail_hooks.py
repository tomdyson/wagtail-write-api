from django.urls import path, reverse

from wagtail import hooks
from wagtail.admin.menu import MenuItem

from wagtail_write_api.views import qr_connect


@hooks.register("register_admin_urls")
def register_qr_connect_url():
    return [
        path("mobile/", qr_connect, name="wagtail_write_api_qr_connect"),
    ]


@hooks.register("register_admin_menu_item")
def register_mobile_menu_item():
    return MenuItem(
        "Mobile app",
        reverse("wagtail_write_api_qr_connect"),
        icon_name="link",
        order=800,
    )
