from django.test import TestCase
from django.test import Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

from django_themes.models import Theme
from django_themes.forms import ThemeAdminFileForm
from django_themes.storage import get_storage_class

class DjangoThemesTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.theme = Theme.objects.create(
            is_active=True,
            author='Test Author',
            name='Test Theme',
            version='1.2.3',
            path='test',
            description='The greatest theme in the world'
        )
        self.su = User.objects.create_superuser('super', '', 'user')
        self.storage = get_storage_class()()

    def login_superuser(self):
        self.client.logout()
        login_result = self.client.login(username='super', password='user')
        self.assertEqual(login_result, True)

    def save_file(self, url, filename, contents):
        # Post new file form
        post_response = self.client.post(url, {'path': filename, 'file_editor': contents})
        self.assertEqual(post_response.status_code, 302)

        # Check that file was created
        full_path = 'test' + filename
        exists = self.storage.exists(full_path)
        self.assertTrue(exists)
        f = self.storage.open(full_path)
        file_contents = f.read()
        self.assertEqual(file_contents.decode('utf-8'), contents)

    def test_view_load(self):
        response = self.client.get('/test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'<p>Best View Ever</p>\n')

    def test_user_exists(self):
        count = User.objects.filter(username='super').count()
        self.assertEqual(count, 1)

    def test_theme_edit_load(self):
        self.login_superuser()
        response = self.client.get('/admin/django_themes/theme/1/change/')
        self.assertEqual(response.status_code, 200)

    def test_theme_custom_edit_load(self):
        self.login_superuser()
        response = self.client.get('/admin/django_themes/theme/1/files/')
        self.assertEqual(response.status_code, 200)

    def test_create_file_form(self):
        # Test ThemeAdminFileForm
        data = {'path': '/myfile.txt', 'file_editor': 'test message'}
        form = ThemeAdminFileForm(data=data)
        self.assertTrue(form.is_valid())

    def test_create_file(self):
        # Get new file form
        self.login_superuser()
        response = self.client.get('/admin/django_themes/theme/1/files//new')
        self.assertEqual(response.status_code, 200)

        # Save file
        self.save_file('/admin/django_themes/theme/1/files//new', '/myfile.txt', 'test message')
