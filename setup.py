# -*- coding: utf-8 -*-
"""Installer for the collective.documentfusion package."""

from setuptools import find_packages
from setuptools import setup


long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')


setup(
    name='collective.documentfusion',
    version='0.1',
    description="Makes a fusion of the variables and of a file field with the other fields of a dexterity content.",
    long_description=long_description,
    # Get more from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 4.3",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
    ],
    keywords='documentation',
    author='Thomas Desvenain',
    author_email='thomasdesvenain@ecreall.com',
    url='http://pypi.python.org/pypi/collective.documentfusion',
    license='GPL',
    packages=find_packages('src', exclude=['ez_setup']),
    namespace_packages=['collective'],
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'plone.api',
        'setuptools',
        'requests',
        'PyPDF2',
        'py3o.fusion',
        'plone.app.dexterity',
        'plone.app.relationfield',
        'plone.behavior',
    ],
    extras_require={
        'test': [
            'ecreall.helpers.testing',
            'plone.app.testing',
        ],
        'async':[
            'plone.app.async',
        ],
    },
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
