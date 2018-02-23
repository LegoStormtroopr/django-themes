import posixpath

from django import forms
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.auth.decorators import permission_required
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.http import Http404
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.translation import ungettext, ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.decorators import method_decorator

from django_themes.models import Theme
from django_themes.utils import add_theme_to_preview, get_previewing_themes, set_themes_to_preview, sizeof_fmt, unset_preview_themes
from django_themes.storage import default_theme_storage
from django_themes.views import ThemeAdminView, EditView, DeleteView, NewView, UploadView, UploadAjaxView


class ThemeAdminForm(forms.ModelForm):

    """
    Custom AdminForm to make the content textarea wider.
    """

    class Meta:
        model = Theme
        fields = ('name', 'author',)
        # fields = "__all__"


class ThemeAdmin(admin.ModelAdmin):
    form = ThemeAdminForm
    fieldsets = (
        (None, {
            'fields': ('author', 'name', 'description'),
        }),
        (_('Advanced'), {
            'fields': (('is_active', 'order', 'path'),),
            'classes': ('monospace',),
        }),
    )

    list_display = ('name', 'is_active','is_previewing', 'order', 'author', 'updated_at')

    save_as = True
    search_fields = ('name', 'description')
    # actions = ['invalidate_cache', 'repopulate_cache', 'check_syntax']
    actions = ['preview_themes', 'stop_preview']

    def get_changelist(self, request, **kwargs):
        self.request = request
        return super(ThemeAdmin, self).get_changelist(request, **kwargs)

    def is_previewing(self, obj):
        return obj.pk in get_previewing_themes(self.request.user)
    is_previewing.short_description = 'Previewing?'
    is_previewing.boolean = True

    def preview_themes(self, request, queryset):
        themes = []
        count = queryset.count()
        set_themes_to_preview(self.request.user, queryset)
        message = _(
            "Now previewing %(count)d templates: %(names)s."
        )
        self.message_user(request, message %
                          {'count': count, 'names': ', '.join(themes)})
    preview_themes.short_description = _("Preview themes")

    def stop_preview(self, request, queryset):
        unset_preview_themes(request.user, queryset)

    def get_urls(self):
        """Returns the additional urls used by the theme editor admin pages."""
        urls = super(ThemeAdmin, self).get_urls()
        admin_site = self.admin_site
        opts = self.model._meta
        info = opts.app_label, opts.model_name,

        print('%s_%s_theme_editor' % info)

        theme_edit_urls = [
            url("^(?P<theme_id>[^/]+)/files/(?P<path>.*?)/edit", admin_site.admin_view(EditView.as_view()), name='admin_edit'),
            url("^(?P<theme_id>[^/]+)/files/(?P<path>.*?)/delete", admin_site.admin_view(DeleteView.as_view()), name='admin_delete'),
            url("^(?P<theme_id>[^/]+)/files/(?P<path>.*?)/new", admin_site.admin_view(NewView.as_view()), name='admin_new'),
            url("^(?P<theme_id>[^/]+)/files/(?P<path>.*?)/upload", admin_site.admin_view(UploadView.as_view()), name='admin_upload'),
            url("^(?P<theme_id>[^/]+)/files/(?P<path>.*?)/upload_ajax", admin_site.admin_view(UploadAjaxView.as_view()), name='admin_upload_ajax'),
            url("^(?P<theme_id>[^/]+)/files/(?P<path>.*?)$", admin_site.admin_view(ThemeAdminView.as_view()), name='%s_%s_theme_editor' % info),
        ]
        return theme_edit_urls + urls

    themes_folder_template = "admin/django_themes/editor/browser.html"
    themes_file_template = "admin/django_themes/editor/browser.html"

admin.site.register(Theme, ThemeAdmin)
