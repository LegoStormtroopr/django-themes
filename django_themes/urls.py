from django.conf import settings
from django.conf.urls import include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name="fileeditor.html")),
    url(r'^connector$', views.Connector.as_view()),
    url(r'^connector/(?P<prefix>.*)$', views.PrefixConnector.as_view()),
]
