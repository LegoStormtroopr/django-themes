from django.conf import settings
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from django.core.files.storage import FileSystemStorage

try:
    from database_files.storage import DatabaseStorage
except:
    DatabaseStorage = None

def get_storage_class(import_path=None):
    module = import_path or settings.THEMES_FILE_STORAGE

    if module == 'dbstorage' and DatabaseStorage:
        return DatabaseStorage()
    else:
        return import_string(module)

class DefaultFileStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(location=settings.THEMES_FILE_ROOT)

if isinstance(get_storage_class(), FileSystemStorage):
    default_theme_storage = DefaultFileStorage()
else:
    default_theme_storage = get_storage_class()
