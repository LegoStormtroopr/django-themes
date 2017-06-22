"""
Wrapper for loading templates from themes.
"""
import errno

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import SuspiciousFileOperation
from django.db.models import Q
from django.template import Origin, TemplateDoesNotExist
from django.utils._os import safe_join

from django_themes.storage import default_theme_storage
from django_themes.models import Theme

from django.template.loaders.base import Loader as BaseLoader
import posixpath


import logging

logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)


class ThemeTemplateLoader(BaseLoader):

    def get_theme_template_path(self, theme, template_name):
        logger.debug("trying -- %s (%s)::%s" % (theme.path, theme.order, template_name))
        path = posixpath.normpath(posixpath.join(theme.path, 'templates', template_name))
        return path

    def get_themes(self):
        from django_themes.middleware import get_current_user_key
        from django_themes.utils import get_previewing_themes
        user_key = get_current_user_key()
        
        preview_pks = []
        if user_key is not None:
            preview_pks = get_previewing_themes(user_key)
        logger.debug("previewing", user_key, preview_pks)
            
        return Theme.objects.all().filter(Q(is_active=True) | Q(pk__in=preview_pks)).order_by('-order')

    def get_contents(self, origin):
        try:
            # with open(origin.name, encoding=self.engine.file_charset) as fp:
            path = self.get_theme_template_path(origin.loader, origin.template_name)
            with default_theme_storage.open(path) as fp:
                logger.debug("serving -- %s::%s" % (origin.loader.path, origin.template_name))
                return fp.read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise TemplateDoesNotExist(origin)
            raise

    def get_template_sources(self, template_name):
        """
        Return an Origin object pointing to an absolute path in each directory
        in template_dirs. For security reasons, if a path doesn't lie inside
        one of the template_dirs it is excluded from the result set.
        """
        for theme in self.get_themes():
            yield Origin(
                name=template_name,
                template_name=template_name,
                loader=theme
            )
