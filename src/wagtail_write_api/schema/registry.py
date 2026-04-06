from wagtail_write_api.schema.generator import generate_schemas_for_model
from wagtail_write_api.settings import api_settings


class SchemaRegistry:
    def __init__(self):
        self._schemas: dict[str, tuple[type, type, type]] = {}
        self._discovered = False

    def register(self, model_class):
        key = f"{model_class._meta.app_label}.{model_class.__name__}"
        self._schemas[key] = generate_schemas_for_model(model_class)

    def auto_discover(self):
        if self._discovered:
            return
        self._discovered = True

        from wagtail.models import Page

        exclude = set(api_settings.EXCLUDE_PAGE_TYPES)
        for model in _get_all_page_models():
            if model._meta.abstract:
                continue
            key = f"{model._meta.app_label}.{model.__name__}"
            if key in exclude:
                continue
            self.register(model)

    def get_schemas(self, type_str: str) -> tuple[type, type, type]:
        self._ensure_discovered()
        return self._schemas[type_str]

    def get_read_schema(self, type_str: str) -> type:
        return self.get_schemas(type_str)[0]

    def get_create_schema(self, type_str: str) -> type:
        return self.get_schemas(type_str)[1]

    def get_patch_schema(self, type_str: str) -> type:
        return self.get_schemas(type_str)[2]

    def all_page_types(self) -> list[str]:
        self._ensure_discovered()
        return list(self._schemas.keys())

    def _ensure_discovered(self):
        if not self._discovered:
            self.auto_discover()


def _get_all_page_models():
    """Get all concrete Page subclasses recursively."""
    from wagtail.models import Page

    result = []

    def _walk(cls):
        for subclass in cls.__subclasses__():
            if not subclass._meta.abstract:
                result.append(subclass)
            _walk(subclass)

    _walk(Page)
    return result


schema_registry = SchemaRegistry()
