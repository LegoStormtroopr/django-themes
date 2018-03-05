from django.views.generic import TemplateView

class TestView(TemplateView):

    template_name = 'testapp/template1.html'
