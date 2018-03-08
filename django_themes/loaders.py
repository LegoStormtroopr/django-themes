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
from django.template.loaders.base import Loader as BaseLoader
from django.template.loaders.cached import Loader as CachedLoader
from django.template import TemplateDoesNotExist
import posixpath

from django_themes.middleware import get_current_user_key
from django_themes.utils import get_previewing_themes
from django_themes.storage import default_theme_storage, encoding
from django_themes.models import Theme

import logging

logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)


class ThemeTemplateLoader(BaseLoader):

    def get_theme_template_path(self, theme, template_name):
        #logger.debug("trying -- %s (%s)::%s" % (theme.path, theme.order, template_name))
        path = posixpath.normpath(posixpath.join(theme.path, 'templates', template_name))
        return path

    def get_themes(self):

        user_key = get_current_user_key()

        preview_pks = []
        if user_key is not None:
            preview_pks = get_previewing_themes(user_key)
        # logger.debug("previewing", user_key, preview_pks)

        return Theme.objects.all().filter(Q(is_active=True) | Q(pk__in=preview_pks)).order_by('-order')

    def get_contents(self, origin):
        try:
            # with open(origin.name, encoding=self.engine.file_charset) as fp:
            path = origin.name
            with default_theme_storage.open(path) as fp:
                if fp is None:
                    raise TemplateDoesNotExist(origin)
                #logger.debug("serving -- %s::%s" % (path, origin.template_name))
                return fp.read().decode(encoding)
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise TemplateDoesNotExist(origin)
            raise
        except AttributeError as e:
            raise TemplateDoesNotExist(origin)


    def get_template_sources(self, template_name):
        """
        Return an Origin object pointing to an absolute path in each directory
        in template_dirs. For security reasons, if a path doesn't lie inside
        one of the template_dirs it is excluded from the result set.
        """
        for theme in self.get_themes():
            path = self.get_theme_template_path(theme, template_name)
            if default_theme_storage.exists(path):
                #logger.debug('Yeilding %s', path)
                yield Origin(
                    name=path,
                    template_name=template_name,
                    loader=self
                )

class CachedThemeTemplateLoader(CachedLoader):

    def __init__(self, engine):
        themeLoader = 'django_themes.loaders.ThemeTemplateLoader'
        loaders = [themeLoader]
        super(CachedThemeTemplateLoader, self).__init__(engine, loaders)

    def get_template(self, template_name, template_dirs=None, skip=None):

        user_key = get_current_user_key()

        preview_pks = []
        if user_key is not None:
            preview_pks = get_previewing_themes(user_key)

        if len(preview_pks) > 0:
            # Don't use the cache
            print('not using cache')
            template = super(CachedLoader, self).get_template(template_name, template_dirs, skip)
        else:
            # Use the cache
            print('using cache')
            template = super(CachedThemeTemplateLoader, self).get_template(template_name, template_dirs, skip)

        return template
