from django.conf import settings

DEFAULTS = {
    "RICH_TEXT_OUTPUT_FORMAT": "html",
    "EXCLUDE_PAGE_TYPES": [],
    "DOCS_URL": "/docs",
    "REQUIRE_AUTH_FOR_READ": True,
    "DEFAULT_PAGE_SIZE": 20,
    "MAX_PAGE_SIZE": 100,
    "IMAGE_RENDITIONS": {
        "thumbnail": "fill-100x100",
        "medium": "max-800x600",
        "large": "max-1600x1200",
    },
}


class ApiSettings:
    def __getattr__(self, name):
        if name not in DEFAULTS:
            raise AttributeError(f"Invalid setting: {name}")
        user_settings = getattr(settings, "WAGTAIL_WRITE_API", {})
        return user_settings.get(name, DEFAULTS[name])


api_settings = ApiSettings()
