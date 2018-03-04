from django.conf import settings
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from django.core.files.storage import FileSystemStorage

def get_storage_class(import_path=None):
    module = import_path or settings.THEMES_FILE_STORAGE
    return import_string(module)

storage_class = get_storage_class()

if issubclass(storage_class, FileSystemStorage):
    default_theme_storage = storage_class(location=settings.THEMES_FILE_ROOT)
else:
    default_theme_storage = storage_class()
