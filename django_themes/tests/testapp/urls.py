from django.conf.urls import include, url
from django.contrib import admin
from django_themes.tests.testapp import views

urlpatterns = [
    url(r'^test', views.TestView.as_view())
]

try:
    from django.urls import path
except ImportError:
    path = None

if path:
    urlpatterns.append(path('admin/', admin.site.urls))
else:
    urlpatterns.append(url(r'^admin/', include(admin.site.urls)))
