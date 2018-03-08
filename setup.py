import os
from setuptools import setup
__version__ = 1.1

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-themes',
    version=__version__,
    packages=['django_themes'],
    include_package_data=True,
    license='MIT License',
    description='Admin extensions to make theming django sites easier for end users of django sites',
    long_description=README,
    url='https://github.com/LegoStormtroopr/django-themes/',
    author='Samuel Spencer',
    author_email='sam@aristotlemetadata.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords='django themes',
    install_requires=['django', 'python-magic'], # I mean obviously you'll have django installed if you want to use this.

)
