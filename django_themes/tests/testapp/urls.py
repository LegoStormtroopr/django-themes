from django.conf.urls import include, url
from django.contrib import admin
from django_themes.tests.testapp import views

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^test', views.TestView.as_view())
]
