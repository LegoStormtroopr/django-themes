django-themes
=============

In brief: Admin extensions to make theming django sites easier for end users of django sites.

Goals
-----
* Serve themes for django using built-in Django FileStorage api - this means themes can be served from `FileSystem`_, `Cloud storage`_ (such as `Amazon S3`_) or from `the database`_
* Follow django admin design, to help it feel like a Django-native process
* Above all: Give end users more control over how their django apps look and behave, without having to change the code used to deploy the app.

.. _`FileSystem`: https://docs.djangoproject.com/en/1.11/ref/files/storage/
.. _`Cloud storage`: http://django-storages.readthedocs.io
.. _`Amazon S3`: https://github.com/etianen/django-s3-storage
.. _`the database`: https://github.com/bfirsh/django-database-files

How to install & configure
--------------------------

1. Install it from PyPI

2. Add Django themes to your ``INSTALLED_APPS``. Django-themes doesn't override anything, so you can put this anywhere in the order::

    INSTALLED_APPS = (
      # ... your other apps
      'django_themes',
    )

3. Add theme directives::

    THEMES_FILE_ROOT = os.getenv('DJANGO_THEMES_ROOT', os.path.join(BASE_DIR, "themes")) # Where your themes are
    THEMES_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage' # Or whatever storage you need

4. If you need to render uploaded templates add the template loader 'django_themes.loaders.ThemeTemplateLoader' to your TEMPLATES setting

5. If you want to be able to preview themes live, add the appropriate middleware *after* everything else.
   Note: to get the current user during template loading, this needs to store the user of a request in ``_thread_locals``.
   `I've read that some Django core devs consider this a security issue, but most people are ok with it <https://groups.google.com/forum/#!topic/django-users/ia9y6L-g34g>`_.::

    MIDDLEWARE = [
      ...
      'django_themes.middleware.PreviewWithCurrentUserMiddleware',
    ]

See it in action
----------------

Drag-and-drop files to add them

.. image:: https://user-images.githubusercontent.com/2173174/27420120-c5b780be-5767-11e7-965d-70b20181d3f6.gif
   :alt: Adding a file

Preview changes to themes before they are active

.. image:: https://user-images.githubusercontent.com/2173174/27420119-c5a586a2-5767-11e7-8b49-90a310a2f03e.gif
   :alt: Previewing a change


Resources
---------

This package uses the following open-source resources:

* `AceJS Code Editor v1.2.7 <https://ace.c9.io//>`_ - Editing widget
* `DropzoneJS v5.0.0 <http://www.dropzonejs.com/>`_ - Drag-and-drop uploading
* `GitHub Octicons v4.3.0 <https://octicons.github.com//>`_ - Font Icons
