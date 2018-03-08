from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.generic import TemplateView, FormView, View
from django.views.generic.base import ContextMixin
from django.shortcuts import get_object_or_404
from django.utils.text import capfirst
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.template.engine import Engine as TemplateEngine
from django.template.exceptions import TemplateDoesNotExist

from django_themes.storage import default_theme_storage, encoding
from django_themes.models import Theme
from django_themes.utils import sizeof_fmt, clear_template_cache
from django_themes.forms import ThemeAdminFileForm, ThemeAdminUploadFileForm, ThemeAdminFolderForm
import posixpath
import magic
import base64
import os
import io
# Admin views

import logging
logger = logging.getLogger(__name__)

class GenericAdminView(PermissionRequiredMixin, TemplateView):

    permission_required = 'django_themes.change_theme'

    context_read_file = False
    opts = None
    theme = None
    path = None
    path_and_parts = None
    template_name = None
    title = ""
    filedata = None

    def dispatch(self, request, theme_id, path):

        self.set_data(theme_id, path)
        return super(GenericAdminView, self).dispatch(request, theme_id, path)

    def join_theme_path(self, theme_path, path):
        full_path = os.path.join(theme_path, path.lstrip('/'))
        if '..' in full_path:
            raise Http404("Illegal Path")
        return full_path

    def read_file(self):

        lines = 0
        contents = ''

        with default_theme_storage.open(self.join_theme_path(self.theme.path, self.path)) as fh:
            contents = fh.read()
            mime = magic.from_buffer(contents, mime=True)
            filetype = mime.split('/')[0]
            size = " ".join(map(str,sizeof_fmt(fh.size)))

            if filetype == 'text':
                for line in fh:
                    lines += 1
            elif filetype == 'image':
                # Base64 encode and decode to unicode string
                data64 = base64.b64encode(contents).decode()
                # Build URI string
                contents = u'data:%s;base64,%s' % (mime, data64)

        file_context = {
            'file' : {
                'contents': contents,
                'lines': lines,
                'size': size,
                'filetype': filetype
            }
        }
        return file_context

    def get_context_data(self, **kwargs):

        context = super(GenericAdminView, self).get_context_data(**kwargs)

        context.update({
            "opts": self.opts,
            "title": self.title,

            "app_label": self.opts.app_label,
            "model_name": capfirst(self.opts.verbose_name),
            "theme": self.theme,
            "path": self.path,
            "paths": self.paths_and_parts,
            "title": "{title} | Theme Editor {theme.name}".format(theme=self.theme, title=self.title)
        })

        if (self.context_read_file and self.filedata):
            context.update(self.filedata)
        elif (self.context_read_file):
            context.update(self.read_file())

        return context

    def set_data(self, theme_id, path):
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

        if (self.context_read_file):
            self.filedata = self.read_file()

    def check_path(self, path):
        # If the file being saved overwrites an existing template, clear the template cache
        # Returns 1 when cleared 0 when not cleared

        search_string = 'templates/'
        index = path.find(search_string)

        if index == -1:
            # If not found
            return 0

        end_index = index + len(search_string)
        template_name = path[end_index:]

        try:
            template = TemplateEngine.get_default().find_template(template_name)
        except TemplateDoesNotExist:
            template = None

        if template:
            # If overriding existing template
            clear_template_cache()
            return 1

        return 0

class ThemeAdminView(GenericAdminView):

    def get(self, request, theme_id, path):

        full_path = self.join_theme_path(self.theme.path, self.path)

        try:
            path = default_theme_storage.path(full_path)
        except NotImplementedError:
            # Will not be implemented in db files
            path = None

        if path:
            # If a system path does not exist
            if not default_theme_storage.exists(path):
                raise Http404('No such directory')
            # If we have a system path can use os.path.isdir to decide
            if os.path.isdir(path):
                _type = "folder"
            else:
                _type = "path"
        else:
            # If not on a real file system use listdir to decide
            folders, files = default_theme_storage.listdir(full_path)
            if files == [] and folders == []:
                _type = "file"
            else:
                _type = "folder"

            if not self.path:
                # If this is the base directory of the theme it must be a folder
                _type = "folder"

        if  _type == "folder":
            return self.render_folder()
        else:
            return self.render_file()

    def render_file(self):

        self.template_name = "admin/django_themes/editor/file_viewer.html"
        self.context_read_file= True

        context = self.get_context_data()
        context['title'] = "Viewing File " + context['title']

        return self.render_to_response(context)

    def render_folder(self):

        self.template_name = "admin/django_themes/editor/browser.html"

        _folders, _files = default_theme_storage.listdir(self.join_theme_path(self.theme.path, self.path))
        folders = [{'name': folder, 'path': posixpath.join(self.path, folder)} for folder in _folders]

        if len(self.paths_and_parts) > 1:
            folders.insert(0,
                {'name': '..', 'path': self.paths_and_parts[-2][-1]}
            )

        files = []

        for file in _files:
            fname = os.path.join(self.theme.path, self.path, file)
            fh = default_theme_storage.open(fname)
            files.append({
                    'name': file,
                    'path': posixpath.join(self.path, file),
                    'size': " ".join(sizeof_fmt(fh.size)),
                    'modified': default_theme_storage.get_modified_time(fname)
                })

        context = self.get_context_data()
        context.update({'files': files, 'folders': folders})
        context['title'] = "Viewing Folder " + context['title']

        return self.render_to_response(context)

class EditView(GenericAdminView, FormView):

    template_name = "admin/django_themes/editor/file_text_editor.html"
    context_read_file = True
    form_class = ThemeAdminFileForm
    title = "Editing File"

    def get_initial(self):
        return {'path':self.path, 'file_editor': self.filedata['file']['contents']}

    def get_success_url(self):
        return reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':self.path})

    def form_valid(self, form):


        post_save_delete_path = None
        if form.cleaned_data['path'] != self.path:
            # Check stuff
            post_save_delete_path = self.path
            path = form.cleaned_data['path']
            self.check_path(path)

            message = "File '%s' saved and renamed successfully!" % self.path
        else:
            message = "File '%s' saved successfully!" % self.path
            path = self.path

        full_path = self.join_theme_path(self.theme.path, path)
        file_editor = form.cleaned_data['file_editor']

        if default_theme_storage.exists(full_path):
            default_theme_storage.delete(full_path)

        file_editor_io = io.BytesIO(file_editor.encode(encoding))
        default_theme_storage.save(full_path, file_editor_io)

        messages.success(self.request, message)
        if post_save_delete_path:
            default_theme_storage.delete(self.join_theme_path(self.theme.path, post_save_delete_path))
            self.path = path # So the redirect goes to new file

        return HttpResponseRedirect(self.get_success_url())

class DeleteView(GenericAdminView):

    template_name = "admin/django_themes/editor/file_delete.html"
    context_read_file = False
    title = "Deleting File"

    def get(self, request, theme_id, path):

        self.context_read_file = True
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, theme_id, path):

        default_theme_storage.delete(self.join_theme_path(self.theme.path, self.path))
        message = "File '%s' deleted successfully!" % path
        messages.success(request, message)
        new_path = ''
        return HttpResponseRedirect(
            reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':new_path})
        )

class NewView(GenericAdminView, FormView):

    template_name = "admin/django_themes/editor/file_text_editor.html"
    form_class = ThemeAdminFileForm
    title = "Creating File"

    def get_initial(self):
        return {'path':self.path+'/new_file', 'file_editor': ''}

    def get_success_url(self):
        return reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':self.path})

    def form_valid(self, form):

        path = form.cleaned_data['path']
        file_editor = form.cleaned_data['file_editor']

        self.check_path(path)

        message = "File '%s' saved successfully!" % path
        full_path = self.join_theme_path(self.theme.path, path)

        if default_theme_storage.exists(full_path):
            return HttpResponse('already exists')

        file_editor_io = io.BytesIO(file_editor.encode(encoding))
        default_theme_storage.save(full_path, file_editor_io)

        messages.success(self.request, message)

        return HttpResponseRedirect(self.get_success_url())

class UploadView(GenericAdminView, FormView):

    template_name = "admin/django_themes/editor/file_upload.html"
    form_class = ThemeAdminUploadFileForm
    title = "Upload File"

    def get_initial(self):
        return {'path':self.path, 'file_editor': ''}

    def get_success_url(self):
        return reverse("admin:django_themes_theme_theme_editor", kwargs={'theme_id':self.theme.pk, 'path':self.path})

    def form_valid(self, form):
        message = "Files uploaded successfully!"

        files = self.request.FILES.getlist('file_upload')
        path = form.cleaned_data['path']
        self.check_path(path)

        for f in files:
            theme_path = self.join_theme_path(self.theme.path, path)
            full_path = os.path.join(theme_path, f.name)
            default_theme_storage.save(full_path, f)

        messages.success(self.request, message)

        return HttpResponseRedirect(self.get_success_url())

class UploadAjaxView(GenericAdminView):

    def post(self, request, theme_id, path):
        submitted_path = request.POST.get('path')
        self.check_path(submitted_path)
        logger.debug('path: %s'%submitted_path)
        try:
            files = request.FILES.getlist('file_upload')
            for f in files:
                theme_path = self.join_theme_path(self.theme.path, submitted_path)
                full_path = os.path.join(theme_path, f.name)
                default_theme_storage.save(full_path, f)
            message = {"ok": "Files uploaded successfully!"}
            code = 200
        except Exception as e:
            message = {"error": str(e)}
            code = 500

        return JsonResponse(message, status=code)
