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
from django_themes.utils import add_theme_to_preview, get_previewing_themes, set_themes_to_preview, sizeof_fmt
from django_themes.storage import default_theme_storage


class ThemeAdminForm(forms.ModelForm):

    """
    Custom AdminForm to make the content textarea wider.
    """

    class Meta:
        model = Theme
        fields = ('name', 'author',)
        # fields = "__all__"

class ThemeAdminFileForm(forms.Form):
    path = forms.CharField()
    file_editor = forms.CharField()

    def clean_path(self):
        path = self.cleaned_data.get("path")

        if '..' in path:
            self.add_error("path", "No relative paths allowed.")
        if path.endswith('/') or path.endswith('\\'):
            self.add_error("path", "A filename must follow be included after a directory separator.")


class ThemeAdminUploadFileForm(forms.Form):
    file_upload = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))

    # def clean_path(self):
    #     path = self.cleaned_data.get("path")

    #     if '..' in path:
    #         self.add_error("path", "No relative paths allowed.")
    #     if path.endswith('/') or path.endswith('\\'):
    #         self.add_error("path", "A filename must follow be included after a directory separator.")


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
    actions = ['preview_themes']

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

    def get_urls(self):
        """Returns the additional urls used by the theme editor admin pages."""
        urls = super(ThemeAdmin, self).get_urls()
        admin_site = self.admin_site
        opts = self.model._meta
        info = opts.app_label, opts.model_name,

        print('%s_%s_theme_editor' % info)

        theme_edit_urls = [
            url("^(?P<theme_id>[^/]+)/files/(?P<path>.*?)$", admin_site.admin_view(self.theme_edit_view), name='%s_%s_theme_editor' % info),
        ]
        return theme_edit_urls + urls

    themes_folder_template = "admin/django_themes/editor/browser.html"
    themes_file_template = "admin/django_themes/editor/browser.html"

    @method_decorator(permission_required('django_themes.change_theme')) # user.has_perm('foo.change_bar')
    def theme_edit_view(self, request, theme_id, path): #request, object_id, path=None):
        permission_required('django_theme.change_theme')

        theme = get_object_or_404(self.model, pk=theme_id)

        path = path.strip('/')
        parts = path.split("/")
        if len(parts) == 1 and parts[0] == '':
            paths_and_parts = []
        else:
            paths_and_parts = [
                (part, "/".join(parts[:i+1]))
                for i, part in enumerate(parts)
            ]
        paths_and_parts.insert(0, (theme.name, ""))

        if request.GET.get('action', None):
            action = request.GET.get('action', None)
            method = {
                'edit': self.edit_file,
                'delete': self.delete_file,
                'new': self.new_file,
                'upload': self.upload_file,
                'upload_ajax': self.upload_file_ajax,
            }.get(action, None)
            print(method)
            if method:
                return method(request, theme, path, paths_and_parts)

        try:
            default_theme_storage.listdir("/".join([theme.path, path]))
            _type = "folder"
        except:
            if not default_theme_storage.exists("/".join([theme.path, path])):
                raise Http404
            _type = "file"

        if  _type == "folder":
            return self.render_folder(request, theme, path, paths_and_parts)
        else:
            return self.render_file(request, theme, path, paths_and_parts)


    def render_file(self, request, theme, path, paths_and_parts):
        opts = self.model._meta

        template = "admin/django_themes/editor/file_text_viewer.html"
        # file
        lines = 0
        contents = ""
        size = None

        with default_theme_storage.open("/".join([theme.path, path])) as fh:
            size = " ".join(map(str,sizeof_fmt(fh.size)))
            contents = fh.read()
            for line in fh:
                lines += 1
        # contents = .read()
        context = {
            "opts": opts,
            "title": "Viewing file {file} | Theme Editor {theme.name}".format(theme=theme, file=path),

            "app_label": opts.app_label,
            "model_name": capfirst(opts.verbose_name),
            "theme": theme,
            "path": path,
            "paths": paths_and_parts,

            "file": {
                    'name': theme.name,
                    'path': path,
                    'contents': contents,
                    'lines': lines,
                    'size': size,
                    'ext': path.split('.')[-1]
                    # 'file': default_theme_storage
                }
        }
        return render(request, template, context)

    def edit_file(self, request, theme, path, paths_and_parts):
        opts = self.model._meta

        form = None
        if request.POST:
            form = ThemeAdminFileForm(request.POST)

            if form.is_valid():

                post_save_delete_path = None
                if request.POST.get('path') != path:
                    # Check stuff
                    post_save_delete_path = path
                    path = request.POST.get('path')

                    message = _("File '%s' saved and renamed successfully!") % path
                else:
                    message = _("File '%s' saved successfully!") % path

                full_path = "/".join([theme.path, path])
                if default_theme_storage.exists(full_path):
                    with default_theme_storage.open(full_path, 'w') as fh:
                        fh.write(request.POST.get('file_editor'))
                else:
                    default_theme_storage.save(full_path, ContentFile(request.POST.get('file_editor')))

                messages.success(request, message)
                if post_save_delete_path:
                    default_theme_storage.delete("/".join([theme.path, post_save_delete_path]))

                return redirect(
                    reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':theme.pk, 'path':path})
                )

        template = "admin/django_themes/editor/file_text_editor.html"

        lines = 0
        contents = ""
        size = None
        with default_theme_storage.open("/".join([theme.path, path])) as fh:
            size = " ".join(map(str,sizeof_fmt(fh.size)))
            contents = fh.read()
            for line in fh:
                lines += 1

        if form is None:
            form = ThemeAdminFileForm(initial={'path':path, 'file_editor': contents})

        context = {
            "opts": opts,
            "title": "Editing file {file} | Theme Editor {theme.name}".format(theme=theme, file=path),

            "app_label": opts.app_label,
            "model_name": capfirst(opts.verbose_name),
            "theme": theme,
            "path": path,
            "paths": paths_and_parts,
            "form": form,
            "file": {
                    'name': path.split('/')[-1],
                    'path': path,
                    'contents': contents,
                    'lines': lines,
                    'size': size,
                    'ext': path.split('.')[-1]
                    # 'file': default_theme_storage
                }
        }
        return render(request, template, context)

    def delete_file(self, request, theme, path, paths_and_parts):
        opts = self.model._meta

        if request.POST:
            default_theme_storage.delete("/".join([theme.path, path]))
            message = _("File '%s' deleted successfully!") % path
            messages.success(request, message)
            return redirect(
                reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':theme.pk, 'path':path.rsplit('/',1)[0]})
            )

        template = "admin/django_themes/editor/file_delete.html"

        lines = 0
        contents = ""
        size = None
        with default_theme_storage.open("/".join([theme.path, path])) as fh:
            size = " ".join(map(str,sizeof_fmt(fh.size)))
            for line in fh:
                lines += 1

        context = {
            "opts": opts,
            "title": "Theme Editor - deleting %s:%s" % (theme, path ,),

            "app_label": opts.app_label,
            "model_name": capfirst(opts.verbose_name),
            "theme": theme,
            "path": path,
            "paths": paths_and_parts,

            "file": {
                    'name': path.split('/')[-1],
                    'path': path,
                    'lines': lines,
                    'size': size,
                    # 'file': default_theme_storage
                }
        }
        return render(request, template, context)

    def render_folder(self, request, theme, path, paths_and_parts):
        opts = self.model._meta
        _folders, _files = default_theme_storage.listdir("/".join([theme.path, path]))
        folders = [{'name': folder, 'path': posixpath.join(path, folder)} for folder in _folders]

        if len(paths_and_parts) > 1:
            folders.insert(0,
                {'name': '..', 'path': paths_and_parts[-2][-1]}
            )

        files = []

        for file in _files:
            fname = "/".join([theme.path, path, file])
            fh = default_theme_storage.open(fname)
            files.append({
                    'name': file,
                    'path': posixpath.join(path, file),
                    'size': " ".join(sizeof_fmt(fh.size)),
                    'modified': default_theme_storage.modified_time(fname)
                })
        context = {
            "opts": opts,
            "title": "Viewing {folder} | Theme Editor {theme.name}".format(theme=theme, folder=path),

            "app_label": opts.app_label,
            "model_name": capfirst(opts.verbose_name),
            "theme": theme,
            "path": path,
            "paths": paths_and_parts,

            "files": files,
            "folders": folders,

        }
        return render(request, self.themes_folder_template, context)

    def new_file(self, request, theme, path, paths_and_parts):
        opts = self.model._meta

        form = None
        if request.POST:
            form = ThemeAdminFileForm(request.POST)

            path = request.POST.get('path')
            if default_theme_storage.exists(path):
                raise Error
            elif form.is_valid():
                message = _("File '%s' saved successfully!") % path

                full_path = "/".join([theme.path, path])
                with default_theme_storage.open(full_path, 'w') as fh:
                    fh.write(request.POST.get('file_editor'))

                messages.success(request, message)

                return redirect(
                    reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':theme.pk, 'path':path})
                )

        template = "admin/django_themes/editor/file_text_editor.html"

        if form is None:
            form = ThemeAdminFileForm(initial={'path':path+'/new_file', 'file_editor': ""})

        context = {
            "opts": opts,
            "title": "Creating new file | Theme Editor {theme.name}".format(theme=theme),

            "app_label": opts.app_label,
            "model_name": capfirst(opts.verbose_name),
            "theme": theme,
            "path": path,
            "paths": paths_and_parts,
            "form": form,
        }
        return render(request, template, context)

    def upload_file(self, request, theme, path, paths_and_parts):
        opts = self.model._meta
        form = None
        if request.POST:
            form = ThemeAdminUploadFileForm(request.POST, request.FILES)

            print(form)
            print(request.POST)
            # path = request.POST.get('path')
            # if default_theme_storage.exists(path):
            #     raise Error
            print("FILES ARE", request.FILES.getlist('file_upload'))
            if form.is_valid():
                message = _("Files uploaded successfully!")


                files = request.FILES.getlist('file_upload')
                for f in files:
                    full_path = "/".join([theme.path, path, f.name])
                    default_theme_storage.save(full_path, f)

                messages.success(request, message)

                return redirect(
                    reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':theme.pk, 'path':path})
                )

        template = "admin/django_themes/editor/file_upload.html"

        if form is None:
            form = ThemeAdminUploadFileForm(initial={'path':path+'/new_file'})

        context = {
            "opts": opts,
            "title": "Upload file | Theme Editor {theme.name}".format(theme=theme),

            "app_label": opts.app_label,
            "model_name": capfirst(opts.verbose_name),
            "theme": theme,
            "path": path,
            "paths": paths_and_parts,
            "form": form,
        }
        return render(request, template, context)

    def upload_file_ajax(self, request, theme, path, paths_and_parts):
        message = {}
        code = 200
        if request.POST:
            print("FILES ARE AJAXY", request.FILES.getlist('file_upload'))
            try:
                files = request.FILES.getlist('file_upload')
                for f in files:
                    full_path = "/".join([theme.path, path, f.name])
                    default_theme_storage.save(full_path, f)
                message = {"ok": _("Files uploaded successfully!")}
                code = 200
            except:
                message = {"error": "WHAT"}
                code = 500
                raise
        else:
            message = {"error": "GET not allowed"}
            code = 400
        return JsonResponse(message, status=code)

admin.site.register(Theme, ThemeAdmin)
