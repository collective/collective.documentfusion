# -*- coding: utf-8 -*-
"""Setup/installation tests for this package."""

import os
import datetime
import tempfile
import subprocess

from zope.event import notify
from zope.component import getUtility
from zope.interface.declarations import alsoProvides
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import ObjectModifiedEvent

from z3c.relationfield.relation import RelationValue

from plone import api
from plone.namedfile.file import NamedFile

from collective.documentfusion.testing import IntegrationTestCase
from collective.documentfusion.interfaces import ICollectiveDocumentfusionLayer


TEST_LETTER_ODT = os.path.join(os.path.dirname(__file__), 'letter.odt')
TEST_LABEL_ODT = os.path.join(os.path.dirname(__file__), 'label.odt')

class TestInstall(IntegrationTestCase):
    """Test installation of collective.documentfusion into Plone."""

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if collective.documentfusion is installed with portal_quickinstaller."""
        self.assertTrue(self.installer.isProductInstalled('collective.documentfusion'))

    def test_uninstall(self):
        """Test if collective.documentfusion is cleanly uninstalled."""
        self.installer.uninstallProducts(['collective.documentfusion'])
        self.assertFalse(self.installer.isProductInstalled('collective.documentfusion'))

    # browserlayer.xml
    def test_browserlayer(self):
        """Test that ICollectiveDocumentfusionLayer is registered."""
        from plone.browserlayer import utils
        self.assertIn(ICollectiveDocumentfusionLayer, utils.registered_layers())

    def test_document_fusion(self):
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        content = api.content.create(self.portal, type='letter',
                           title=u"En réponse...",
                           file=NamedFile(data=open(TEST_LETTER_ODT).read(),
                                          filename=u'letter.odt',
                                          contentType='application/vnd.oasis.opendocument.text'),
                           sender_name="Thomas Desvenain",
                           sender_address="57 Quai du Pré Long",
                           recipient_name="Vincent Fretin",
                           date=datetime.date(2012, 12, 23))

        notify(ObjectModifiedEvent(content))
        generated_stream = content.unrestrictedTraverse('@@getdocumentfusion')()
        self.assertTrue(generated_stream)
        self.assertEqual(self.portal.REQUEST.response['content-type'],
                         'application/pdf')
        generated_path = tempfile.mktemp(suffix='letter.pdf')
        generated_file = open(generated_path, 'w')
        generated_file.write(generated_stream.read())
        generated_file.close()

        txt_path = tempfile.mktemp(suffix='letter.pdf')
        subprocess.call(['pdftotext', generated_path, txt_path])
        txt = open(txt_path).read()
        self.assertIn('Vincent Fretin', txt)
        self.assertIn('57 Quai du Pré Long', txt)
        self.assertIn('2012', txt)
        self.assertIn(u'EN RÉPONSE...', txt)

        os.remove(txt_path)
        os.remove(generated_path)

    def test_document_fusion_with_external_source(self):
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        intids = getUtility(IIntIds)
        source_1 = api.content.create(self.portal, type='contact_infos',
                                      id='desvenain_thomas',
                                      identity='M. Desvenain Thomas',
                                      address_1='24 rue des Trois Mollettes',
                                      address_2='C24',
                                      zipcode='59000',
                                      city='Lille')

        content = api.content.create(self.portal, type='label_model',
                           title=u"Modèle d'étiquette",
                           file=NamedFile(data=open(TEST_LABEL_ODT).read(),
                                          filename=u'label.odt',
                                          contentType='application/vnd.oasis.opendocument.text'),
                           relatedItems=[RelationValue(intids.getId(source_1))],
                           )

        notify(ObjectModifiedEvent(content))

        generated_stream = content.unrestrictedTraverse('@@getdocumentfusion')()
        self.assertTrue(generated_stream)
        self.assertEqual(self.portal.REQUEST.response['content-type'],
                         'application/pdf')
        generated_path = tempfile.mktemp(suffix='label.pdf')
        generated_file = open(generated_path, 'w')
        generated_file.write(generated_stream.read())
        generated_file.close()

        txt_path = tempfile.mktemp(suffix='label.pdf')
        subprocess.call(['pdftotext', generated_path, txt_path])
        txt = open(txt_path).read()
        self.assertIn('M. DESVENAIN THOMAS', txt)
        self.assertIn('24 RUE DES TROIS MOLLETTES', txt)
        self.assertIn('C24', txt)
        self.assertIn(u'59000', txt)
        os.remove(txt_path)
        os.remove(generated_path)
