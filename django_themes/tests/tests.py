from django.test import TestCase, override_settings
from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.urls import reverse

from django_themes.models import Theme
from django_themes.forms import ThemeAdminFileForm
from django_themes.storage import get_theme_storage

from os.path import join as pathjoin
from io import BytesIO
import glob
import os

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
        self.su = get_user_model().objects.create_superuser('super', '', 'user')
        self.storage = get_theme_storage()
        print(self.storage)

    # ----------- Util Functions ---------------

    def login_superuser(self):
        self.client.logout()
        login_result = self.client.login(username='super', password='user')
        self.assertEqual(login_result, True)

    def save_file(self, url, filename, contents, theme):
        # Post new file form
        post_response = self.client.post(url, {'path': filename, 'file_editor': contents})
        self.assertEqual(post_response.status_code, 302)

        # Check that file was created
        self.check_file_saved(filename, contents, theme)

    def upload_file(self, url, filename, path, contents, theme):
        # Post to upload page
        testfile = BytesIO(contents.encode('utf-8'))
        testfile.name = filename
        post_response = self.client.post('/admin/django_themes/theme/1/files//upload', {'path': path, 'file_upload': testfile})
        self.assertEqual(post_response.status_code, 302)

        self.check_file_saved(path + filename, contents, theme)

    def check_file_saved(self, filename, contents, theme):
        # Check that file was created
        full_path = pathjoin(theme.path, filename.lstrip('/'))
        exists = self.storage.exists(full_path)
        self.assertTrue(exists)
        f = self.storage.open(full_path)
        file_contents = f.read()
        self.assertEqual(file_contents.decode('utf-8'), contents)

    def check_render_folder(self, url, files, folders):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['files']), files)
        self.assertEqual(len(response.context['folders']), folders)

    # -------------------- Tests -------------------------------

    def test_create_file_in_folder(self):
        self.login_superuser()

        # Save and check file in directory
        self.save_file('/admin/django_themes/theme/1/files//new', '/test/folder/file.txt', 'this is a test broadcast', self.theme)

    def test_view_load(self):
        response = self.client.get('/test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'<p>Best View Ever</p>\n')

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

        # Test with good data
        data = {'path': '/myfile.txt', 'file_editor': 'test message'}
        form = ThemeAdminFileForm(data=data)
        self.assertTrue(form.is_valid())
        # Test with .. in filename
        data = {'path': '/wow/../myfile.txt', 'file_editor': 'test message'}
        form = ThemeAdminFileForm(data=data)
        self.assertFalse(form.is_valid())
        # Test with directory instead of file
        data = {'path': '/good/one/', 'file_editor': 'test message'}
        form = ThemeAdminFileForm(data=data)
        self.assertFalse(form.is_valid())

    def test_create_file(self):
        # Get new file form
        self.login_superuser()
        response = self.client.get('/admin/django_themes/theme/1/files//new')
        self.assertEqual(response.status_code, 200)

        # Save and check file
        self.save_file('/admin/django_themes/theme/1/files//new', '/myfile.txt', 'test message', self.theme)

    def test_render_folders(self):
        self.login_superuser()

        # Save files
        self.save_file('/admin/django_themes/theme/1/files//new', '/myfile.txt', 'test message', self.theme)
        self.save_file('/admin/django_themes/theme/1/files//new', '/test/folder/file.txt', 'this is a test broadcast', self.theme)

        # Load base
        self.check_render_folder('/admin/django_themes/theme/1/files/', 1, 1)

        # Load /test, account for .. folder
        self.check_render_folder('/admin/django_themes/theme/1/files/test', 0, 2)

        # Load /test/folder, account for .. folder
        self.check_render_folder('/admin/django_themes/theme/1/files/test/folder', 1, 1)

    def test_render_file(self):
        # Need to check mimetype filtering
        self.login_superuser()
        self.save_file('/admin/django_themes/theme/1/files//new', '/checkfile.txt', 'very nice message', self.theme)

        response = self.client.get('/admin/django_themes/theme/1/files/checkfile.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['file']['contents'].decode('utf-8'), 'very nice message')
        self.assertEqual(response.context['file']['lines'], 1)
        self.assertEqual(response.context['file']['filetype'], 'text')

    def test_edit_file(self):
        self.login_superuser()
        # Save test file
        self.save_file('/admin/django_themes/theme/1/files//new', '/editfile.txt', 'please change this', self.theme)

        # Load edit page
        response = self.client.get('/admin/django_themes/theme/1/files/editfile.txt/edit')
        self.assertEqual(response.status_code, 200)

        self.save_file('/admin/django_themes/theme/1/files/editfile.txt/edit', 'editfile.txt', 'we changed it', self.theme)

    def test_delete_file(self):
        self.login_superuser()
        # Save test file
        self.save_file('/admin/django_themes/theme/1/files//new', '/deletefile.txt', 'we deleting this', self.theme)

        # Load delete page
        response = self.client.get('/admin/django_themes/theme/1/files/deletefile.txt/delete')
        self.assertEqual(response.status_code, 200)
        # Post to delete page
        post_response = self.client.post('/admin/django_themes/theme/1/files/deletefile.txt/delete')
        self.assertEqual(post_response.status_code, 302)
        # Check that the file was actually deleted
        exists = self.storage.exists('test/deletefile.txt')
        self.assertFalse(exists)

    def test_upload_file(self):
        self.login_superuser()
        # Load upload page
        response = self.client.get('/admin/django_themes/theme/1/files//upload')
        self.assertEqual(response.status_code, 200)

        # Post to upload page and check result
        self.upload_file('/admin/django_themes/theme/1/files//upload', 'realfile.txt', '/', 'actual file data', self.theme)

    def test_upload_file_path(self):
        # Testing uploading to a new path
        self.login_superuser()

        # Post to upload page and check result
        self.upload_file('/admin/django_themes/theme/1/files//upload', 'realfile.txt', '/directory/', 'very good data', self.theme)

    def test_upload_file_ajax(self):
        # Testing uploading to a new path
        self.login_superuser()

        # Post to upload page and check result
        self.upload_file('/admin/django_themes/theme/1/files//ajax_upload', 'realfile.txt', '/', 'ajax file', self.theme)

    def test_upload_view_image(self):
        self.login_superuser()

        # Post to upload page and check result
        with open(pathjoin(settings.BASE_DIR, 'testimage.png'), mode='rb') as fp:
            post_response = self.client.post('/admin/django_themes/theme/1/files//upload', {'path': '/', 'file_upload': fp})
        self.assertEqual(post_response.status_code, 302)

        response = self.client.get('/admin/django_themes/theme/1/files/testimage.png')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['file']['contents'].startswith('data:'))
        self.assertEqual(response.context['file']['lines'], 0)
        self.assertEqual(response.context['file']['filetype'], 'image')

    def test_template_loading(self):
        self.login_superuser()
        # Save test file
        self.save_file('/admin/django_themes/theme/1/files//new', '/templates/testapp/template1.html', '<p>Updated Page</p>', self.theme)

        response = self.client.get('/test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'<p>Updated Page</p>')

    def test_template_loading_multi_theme(self):
        # Test template loading when a template is present in multiple themes
        self.login_superuser()

        secondtheme = Theme.objects.create(
            order=2,
            is_active=True,
            author='New Author',
            name='New Theme',
            version='1.2.3',
            path='new',
            description='The greatest theme in the world'
        )

        # Save the template in 2 different themes
        self.save_file('/admin/django_themes/theme/1/files//new', '/templates/testapp/template1.html', '<p>Updated Page</p>', self.theme)
        self.save_file('/admin/django_themes/theme/2/files//new', '/templates/testapp/template1.html', '<p>Brand New Page</p>', secondtheme)
        # Check that the theme with higher order was used
        response = self.client.get('/test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'<p>Brand New Page</p>')
        # Set second theme to inactive
        secondtheme.is_active=False
        secondtheme.save()
        # Check first theme used
        response = self.client.get('/test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'<p>Updated Page</p>')

    def test_template_preview(self):
        # Test template preview functionality
        self.login_superuser()

        # Make theme inactive
        self.theme.is_active = False
        self.theme.save()

        # Save a template to the theme
        self.save_file('/admin/django_themes/theme/1/files//new', '/templates/testapp/template1.html', '<p>Preview Page</p>', self.theme)

        # Get theme view
        get_response = self.client.get('/admin/django_themes/theme/')
        self.assertEqual(get_response.status_code, 200)

        # Post to change view, with theme selected to preview
        postdata = {
            'action': 'preview_themes',
            ACTION_CHECKBOX_NAME: [self.theme.pk],
        }
        post_response = self.client.post('/admin/django_themes/theme/', postdata)
        self.assertEqual(post_response.status_code, 302)

        # Load test page to see if updated template was rendered
        test_page_response = self.client.get('/test')
        self.assertEqual(test_page_response.content, b'<p>Preview Page</p>')

        # Post to change view, with theme selected to stop preview
        postdata = {
            'action': 'stop_preview',
            ACTION_CHECKBOX_NAME: [self.theme.pk],
        }
        post_response2 = self.client.post('/admin/django_themes/theme/', postdata)
        self.assertEqual(post_response2.status_code, 302)

        # Load test page to see if original template was rendered
        test_page_response = self.client.get('/test')
        self.assertEqual(test_page_response.content, b'<p>Best View Ever</p>\n')

    def test_template_preview_user(self):
        # Test that only the user who selected to preview the theme is shown it's templates
        self.login_superuser()

        # Make theme inactive
        self.theme.is_active = False
        self.theme.save()

        # Save a template to the theme
        self.save_file('/admin/django_themes/theme/1/files//new', '/templates/testapp/template1.html', '<p>Preview Page</p>', self.theme)

        # Post to change view, with theme selected to preview
        postdata = {
            'action': 'preview_themes',
            ACTION_CHECKBOX_NAME: [self.theme.pk],
        }
        post_response = self.client.post('/admin/django_themes/theme/', postdata)
        self.assertEqual(post_response.status_code, 302)

        # Load test page to see if updated template was rendered
        test_page_response = self.client.get('/test')
        self.assertEqual(test_page_response.content, b'<p>Preview Page</p>')

        # Login to different user
        get_user_model().objects.create_user('regular', '', 'user')
        self.client.logout()
        login_result = self.client.login(username='regular', password='user')
        self.assertTrue(login_result)

        # Load test page to see if original template was rendered
        test_page_response = self.client.get('/test')
        self.assertEqual(test_page_response.content, b'<p>Best View Ever</p>\n')


@override_settings(THEMES_FILE_STORAGE='django.core.files.storage.FileSystemStorage')
class DjangoThemesFilesystemTestCase(DjangoThemesTestCase):
    # Run the same tests using file system storage

    # @classmethod
    # def setUpClass(cls):
    #     super().setUpClass()
    #     Storage.set_theme_storage()

    def tearDown(self):
        # Delete all files in directory after each test
        files = glob.glob(settings.THEMES_FILE_ROOT + '/*')
        for f in files:
            os.remove(f)

    def test_create_folder(self):

        self.login_superuser()

        self.client.post('/admin/django_themes/theme/1/files//create_folder', {'folder_name': 'testfolder'})
        full_path = pathjoin(theme.path, 'testfolder')
        exists = self.storage.exists(full_path)
        self.assertTrue(exists)
