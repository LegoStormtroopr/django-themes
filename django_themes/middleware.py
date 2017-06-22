from __future__ import absolute_import, division, print_function

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

def get_current_user_key():
    """ returns the request object for this thread """
    return getattr(_thread_locals, "current_user_key", None)

class PreviewWithCurrentUserMiddleware(object):
    """ Simple middleware that adds the request object in thread local storage."""

    def process_request(self, request):
        if hasattr(request, 'user'):
            _thread_locals.current_user_key = request.user.pk

    def process_response(self, request, response):
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
        return response
