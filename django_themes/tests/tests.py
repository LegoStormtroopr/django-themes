from django.test import TestCase
from django.test import Client

class DjangoThemesTestCase(TestCase):

    def setUp(self):
        self.client = Client()

    def test_view_load(self):
        response = self.client.get('/test')
        self.assertEqual(response.status_code, 200)
