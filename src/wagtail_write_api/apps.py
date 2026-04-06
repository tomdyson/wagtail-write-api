from django.apps import AppConfig


class WagtailWriteApiConfig(AppConfig):
    name = "wagtail_write_api"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Wagtail Write API"

    def ready(self):
        from wagtail_write_api.schema.registry import schema_registry

        schema_registry.auto_discover()
