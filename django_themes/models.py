from django.db import models
from django.db.models import signals
from django.template import TemplateDoesNotExist
from django.utils.translation import ugettext_lazy as _

from django.utils.timezone import now


class Theme(models.Model):
    """
    Defines a template model for use with the database template loader.
    The field ``name`` is the equivalent to the filename of a static template.
    """
    class Meta:
        ordering = ['-order',]
    order = models.PositiveIntegerField(
        default=1,
        help_text=_("The order of themes for resolution of static and template files, higher ranked themes will override ")
    )
    is_active = models.BooleanField(
        default=False,
        help_text=_("")
    )
    author = models.CharField(
        _('author'), max_length=256,
        help_text=_("")
    )
    name = models.CharField(
        _('name'), max_length=256,
        help_text=_("The name of this theme")
    )
    version = models.CharField(
        _('version'), max_length=256, help_text=_("")
    )
    path = models.CharField(
        _('path'), max_length=256, help_text=_("")
    )
    description = models.TextField(
        _('description'),
        help_text=_("A brief description of the files in this theme."),
        blank=True
    )
    # content = models.TextField(_('content'), blank=True)
    # sites = models.ManyToManyField(Site, verbose_name=_(u'sites'),
    #                               blank=True)
    # subthemes = models.ManyToManyField('self', verbose_name=_(u'sites'),
    #                               blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name