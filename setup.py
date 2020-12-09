import io
import os
import re
import sys
from setuptools import setup, find_packages

PATH_BASE = os.path.dirname(__file__)


def read_file(fpath):
    """Reads a file within package directories."""
    with io.open(os.path.join(PATH_BASE, fpath)) as f:
        return f.read()


def get_version():
    """Returns version number, without module import (which can lead to ImportError
    if some dependencies are unavailable before install."""
    contents = read_file(os.path.join('pycbrf', '__init__.py'))
    version = re.search('VERSION = \(([^)]+)\)', contents)
    version = version.group(1).replace(', ', '.').strip()
    return version


setup(
    name='pycbrf',
    version=get_version(),
    url='https://github.com/idlesign/pycbrf',

    description='Tools to query Bank of Russia',
    long_description=read_file('README.rst'),
    license='BSD 3-Clause License',

    author='Igor `idle sign` Starikov',
    author_email='idlesign@yandex.ru',

    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,

    install_requires=[
        'requests',
        'dbf_light>=0.3.0',
    ],
    setup_requires=[] + (['pytest-runner'] if 'test' in sys.argv else []),
    tests_require=[
        'pytest',
        'pytest-datafixtures>=1.0.0',
    ],
    extras_require={
        'cli': ['click'],
    },

    entry_points={
        'console_scripts': ['pycbrf = pycbrf.cli:main'],
    },

    test_suite='tests',

    classifiers=[
        # As in https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: BSD License',
    ],
)
