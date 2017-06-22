from django.conf import settings
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string


def get_storage_class(import_path=None):
    return import_string(import_path or settings.THEMES_FILE_STORAGE)


class DefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class()(location=settings.THEMES_FILE_ROOT)


default_theme_storage = DefaultStorage()
