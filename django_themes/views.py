from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.generic import TemplateView, FormView, View
from django.views.generic.base import ContextMixin


from .file_manager import FileManager




class Connector(View, ContextMixin):
    response_class = JsonResponse
    file_manager_class = FileManager
    storage = default_storage

    def get_file_manager(self):
        return self.file_manager_class(storage=self.storage)
    
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        kwargs = self.request.GET.copy()
        mode = kwargs.pop('mode')[0]
        path = kwargs.pop('path', [""])[0].lstrip("/")
        file_manager = self.get_file_manager()
        # kwargs['is_ajax'] = self.request.is_ajax()
        print(self.request.is_ajax())
        return getattr(file_manager, mode)(path, is_ajax=self.request.is_ajax(), **kwargs)


    def post(self, request, *args, **kwargs):
        kwargs = self.request.POST.copy()
        mode = kwargs.pop('mode')[0]
        path = kwargs.pop('path', [""])[0].lstrip("/")
        file_manager = self.get_file_manager()
        
        return getattr(file_manager, mode)(path, **kwargs)


class PrefixConnector(Connector):
    prefix = "example"
    
    def get_prefix(self):
        return self.prefix
    
    def get_file_manager(self):
        return self.file_manager_class(storage=self.storage, root=self.get_prefix())
