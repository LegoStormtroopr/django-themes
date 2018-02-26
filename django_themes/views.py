from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.generic import TemplateView, FormView, View
from django.views.generic.base import ContextMixin
from django.shortcuts import get_object_or_404
from django.utils.text import capfirst
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
# from .file_manager import FileManager

from django_themes.storage import default_theme_storage
from django_themes.models import Theme
from django_themes.utils import sizeof_fmt
from django_themes.forms import ThemeAdminFileForm, ThemeAdminUploadFileForm

import posixpath
import magic
# Admin views

class GenericAdminView(PermissionRequiredMixin, TemplateView):

    permission_required = 'django_themes.change_theme'

    context_read_file = False
    opts = None
    theme = None
    path = None
    path_and_parts = None
    template_name = None
    title = None

    def dispatch(self, request, theme_id, path):

        self.set_data(theme_id, path)
        return super(GenericAdminView, self).dispatch(request, theme_id, path)

    def read_file(self):

        lines = 0
        contents = ''

        with default_theme_storage.open("/".join([self.theme.path, self.path])) as fh:
            contents = fh.read()
            mime = magic.from_buffer(contents, mime=True)
            filetype = mime.split('/')[0]
            size = " ".join(map(str,sizeof_fmt(fh.size)))

            if filetype == 'text':
                for line in fh:
                    lines += 1

        file_context = {
            'file' : {
                'contents': contents,
                'lines': lines,
                'size': size,
                'filetype': filetype
            }
        }
        return file_context

    def get_context_data(self):

        context = super(GenericAdminView, self).get_context_data()

        context.update({
            "opts": self.opts,
            "title": self.title,

            "app_label": self.opts.app_label,
            "model_name": capfirst(self.opts.verbose_name),
            "theme": self.theme,
            "path": self.path,
            "paths": self.paths_and_parts,
            "title": "| Theme Editor {theme.name}".format(theme=self.theme)
        })

        if (self.context_read_file):
            context.update(self.read_file())

        return context

    def set_data(self, theme_id, path):
        # permission_required('django_theme.change_theme')
        self.theme = get_object_or_404(Theme, pk=theme_id)

        self.opts = self.theme._meta

        self.path = path.strip('/')
        self.parts = self.path.split("/")
        if len(self.parts) == 1 and self.parts[0] == '':
            self.paths_and_parts = []
        else:
            self.paths_and_parts = [
                (part, "/".join(self.parts[:i+1]))
                for i, part in enumerate(self.parts)
            ]
        self.paths_and_parts.insert(0, (self.theme.name, ""))


class ThemeAdminView(GenericAdminView):

    def get(self, request, theme_id, path):

        full_path = "/".join([self.theme.path, self.path])

        try:
            # Try to list dir (check if folder)
            default_theme_storage.listdir(full_path)
            _type = "folder"
        except:
            if not default_theme_storage.exists(full_path):
                # If the path doesn't exist
                return HttpResponse('No such directory %s/%s' % (settings.THEMES_FILE_ROOT, full_path))
            # If not directory but file exists
            _type = "file"

        if  _type == "folder":
            return self.render_folder()
        else:
            return self.render_file()

    def render_file(self):

        self.template_name = "admin/django_themes/editor/file_text_viewer.html"
        self.context_read_file= True

        context = self.get_context_data()
        context['title'] = "Viewing File " + context['title']

        return self.render_to_response(context)

    def render_folder(self):

        self.template_name = "admin/django_themes/editor/browser.html"

        _folders, _files = default_theme_storage.listdir("/".join([self.theme.path, self.path]))
        folders = [{'name': folder, 'path': posixpath.join(self.path, folder)} for folder in _folders]

        if len(self.paths_and_parts) > 1:
            folders.insert(0,
                {'name': '..', 'path': self.paths_and_parts[-2][-1]}
            )

        files = []

        for file in _files:
            fname = "/".join([self.theme.path, self.path, file])
            fh = default_theme_storage.open(fname)
            files.append({
                    'name': file,
                    'path': posixpath.join(self.path, file),
                    'size': " ".join(sizeof_fmt(fh.size)),
                    'modified': default_theme_storage.modified_time(fname)
                })

        context = self.get_context_data()
        context.update({'files': files, 'folders': folders})
        context['title'] = "Viewing Folder " + context['title']

        return self.render_to_response(context)

class EditView(GenericAdminView):

    template_name = "admin/django_themes/editor/file_text_editor.html"
    context_read_file = True
    form = None

    def get(self, request, theme_id, path):

        context = self.get_context_data()

        if self.form is None:
            self.form = ThemeAdminFileForm(initial={'path':self.path, 'file_editor': context['file']['contents']})

        context.update({'form': self.form})
        context['title'] = "Editing File " + context['title']

        return self.render_to_response(context)

    def post(self, request, theme_id, path):

        form = ThemeAdminFileForm(request.POST)

        if form.is_valid():

            post_save_delete_path = None
            if request.POST.get('path') != self.path:
                # Check stuff
                post_save_delete_path = self.path
                path = request.POST.get('path')

                message = "File '%s' saved and renamed successfully!" % self.path
            else:
                message = "File '%s' saved successfully!" % self.path

            full_path = "/".join([self.theme.path, self.path])
            if default_theme_storage.exists(full_path):
                with default_theme_storage.open(full_path, 'w') as fh:
                    fh.write(request.POST.get('file_editor'))
            else:
                default_theme_storage.save(full_path, ContentFile(request.POST.get('file_editor')))

            messages.success(request, message)
            if post_save_delete_path:
                default_theme_storage.delete("/".join([theme.path, post_save_delete_path]))

            return HttpResponseRedirect(
                reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':self.path})
            )

class DeleteView(GenericAdminView):

    template_name = "admin/django_themes/editor/file_delete.html"
    context_read_file = True

    def get(self, request, theme_id, path):

        context = self.get_context_data()
        context['title'] = "Deleting File " + context['title']

        return self.render_to_response(context)

    def post(self, request, theme_id, path):

        self.file_read = False

        default_theme_storage.delete("/".join([self.theme.path, self.path]))
        message = "File '%s' deleted successfully!" % path
        messages.success(request, message)
        return HttpResponseRedirect(
            reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':self.path.rsplit('/',1)[0]})
        )

class NewView(GenericAdminView):

    template_name = "admin/django_themes/editor/file_text_editor.html"
    form = None

    def get(self, request, theme_id, path):

        context = self.get_context_data()

        if self.form is None:
            self.form = ThemeAdminFileForm(initial={'path':self.path+'/new_file', 'file_editor': ''})

        context.update({'form': self.form})
        context['title'] = "Creating File " + context['title']

        return self.render_to_response(context)

    def post(self, request, theme_id, path):

        form = ThemeAdminFileForm(request.POST)

        path = request.POST.get('path')
        if default_theme_storage.exists(path):
            raise Error
        elif form.is_valid():
            message = "File '%s' saved successfully!" % path

            full_path = "/".join([self.theme.path, path])
            with default_theme_storage.open(full_path, 'w') as fh:
                fh.write(request.POST.get('file_editor'))

            messages.success(request, message)

            return HttpResponseRedirect(
                reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':path})
            )

class UploadView(GenericAdminView):

    template_name = "admin/django_themes/editor/file_upload.html"
    form = None

    def get(self, request, theme_id, path):

        context = self.get_context_data()

        if self.form is None:
            self.form = ThemeAdminUploadFileForm(initial={'path':self.path+'/new_file', 'file_editor': ''})

        context.update({'form': self.form})
        context['title'] = "Upload File " + context['title']

        return self.render_to_response(context)

    def post(self, request, theme_id, path):

        message = "Files uploaded successfully!"

        files = request.FILES.getlist('file_upload')
        for f in files:
            full_path = "/".join([self.theme.path, self.path, f.name])
            default_theme_storage.save(full_path, f)

        messages.success(request, message)

        return HttpResponseRedirect(
            reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':self.path})
        )

class UploadAjaxView(GenericAdminView):

    def post(self, request, theme_id, path):

        try:
            files = request.FILES.getlist('file_upload')
            for f in files:
                full_path = "/".join([self.theme.path, self.path, f.name])
                default_theme_storage.save(full_path, f)
            message = {"ok": _("Files uploaded successfully!")}
            code = 200
        except:
            message = {"error": "WHAT"}
            code = 500

        return JsonResponse(message, status=code)
