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
from zope.annotation.interfaces import IAnnotations

from z3c.relationfield.relation import RelationValue

from plone import api
from plone.namedfile.file import NamedFile
from plone.app.blob.adapters.file import BlobbableFile

from collective.documentfusion.testing import IntegrationTestCase
from collective.documentfusion.interfaces import ICollectiveDocumentfusionLayer
from collective.documentfusion.interfaces import (
    STATUS_STORAGE_KEY, TASK_SUCCEEDED)


TEST_LETTER_ODT = os.path.join(os.path.dirname(__file__), 'letter.odt')
TEST_LABEL_ODT = os.path.join(os.path.dirname(__file__), 'label.odt')
TEST_INVOICE_ODT = os.path.join(os.path.dirname(__file__), 'invoice.odt')


class TestInstall(IntegrationTestCase):
    """Test installation of collective.documentfusion into Plone."""

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_document_fusion(self):
        # data source and model are in the same content
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

        annotations = IAnnotations(content)
        status = annotations.get(STATUS_STORAGE_KEY, None)
        self.assertEqual(status, TASK_SUCCEEDED)

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
        txt = open(txt_path).read().replace('\xc2\xa', ' ')
        self.assertIn('Vincent Fretin', txt)
        self.assertIn('57 Quai du Pré Long', txt)
        self.assertIn('2012', txt)
        self.assertIn(u'EN RÉPONSE...', txt)

        os.remove(txt_path)
        os.remove(generated_path)

    def test_document_fusion_with_merge_simple(self):
        # data source is in a related content
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
        txt = open(txt_path).read().replace('\xc2\xa', ' ')
        self.assertIn('M. DESVENAIN THOMAS', txt)
        self.assertIn('24 RUE DES TROIS MOLLETTES', txt)
        self.assertIn('C24', txt)
        self.assertIn(u'59000', txt)
        os.remove(txt_path)
        os.remove(generated_path)

    def test_document_fusion_with_merge_multiple(self):
        # data source is in a related content
        # we merge two files from two sources
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        intids = getUtility(IIntIds)
        source_1 = api.content.create(self.portal, type='contact_infos',
                                      id='desvenain_thomas',
                                      identity='M. Desvenain Thomas',
                                      address_1='24 rue des Trois Mollettes',
                                      address_2='C24',
                                      zipcode='59000',
                                      city='Lille')

        source_2 = api.content.create(self.portal, type='contact_infos',
                                      id='fretin_vincent',
                                      identity='M. Fretin Vincent',
                                      address_1='51 r Lac',
                                      address_2='',
                                      zipcode='59810',
                                      city='LESQUIN')

        content = api.content.create(self.portal, type='label_model',
                           title=u"Modèle d'étiquette",
                           file=NamedFile(data=open(TEST_LABEL_ODT).read(),
                                          filename=u'label.odt',
                                          contentType='application/vnd.oasis.opendocument.text'),
                           relatedItems=[RelationValue(intids.getId(source_1)),
                                         RelationValue(intids.getId(source_2))],
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
        txt = open(txt_path).read().replace('\xc2\xa', ' ')

        # label 1
        self.assertIn('M. DESVENAIN THOMAS', txt)
        self.assertIn('24 RUE DES TROIS MOLLETTES', txt)
        self.assertIn('C24', txt)
        self.assertIn(u'59000', txt)

        # label 2
        self.assertIn('M. FRETIN VINCENT', txt)
        self.assertIn(u'59810', txt)
        self.assertIn(u'LESQUIN', txt)

        os.remove(txt_path)
        os.remove(generated_path)

    def test_document_fusion_with_merge_multiple_collection(self):
        # data source is in a related content
        # we merge two files from two sources
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        intids = getUtility(IIntIds)
        api.content.create(self.portal, type='contact_infos',
                           id='desvenain_thomas',
                           identity='M. Desvenain Thomas',
                           address_1='24 rue des Trois Mollettes',
                           address_2='C24',
                           zipcode='59000',
                           city='Lille')

        api.content.create(self.portal, type='contact_infos',
                           id='fretin_vincent',
                           identity='M. Fretin Vincent',
                           address_1='51 r Lac',
                           address_2='',
                           zipcode='59810',
                           city='LESQUIN')

        collection = api.content.create(self.portal, type='Collection',
                    id='all_labels',
                    query=[{'i': 'portal_type',
                            'o': 'plone.app.querystring.operation.selection.is',
                            'v': ['contact_infos']}])

        content = api.content.create(self.portal, type='label_model',
                           title=u"Modèle d'étiquette",
                           file=NamedFile(data=open(TEST_LABEL_ODT).read(),
                                          filename=u'label.odt',
                                          contentType='application/vnd.oasis.opendocument.text'),
                           relatedItems=[RelationValue(intids.getId(collection))],
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

        # label 1
        self.assertIn('M. DESVENAIN THOMAS', txt)
        self.assertIn('24 RUE DES TROIS MOLLETTES', txt)
        self.assertIn('C24', txt)
        self.assertIn(u'59000', txt)

        # label 2
        self.assertIn('M. FRETIN VINCENT', txt)
        self.assertIn(u'59810', txt)
        self.assertIn(u'LESQUIN', txt)

        os.remove(txt_path)
        os.remove(generated_path)

    def test_document_fusion_with_external_model(self):
        # model is in a related content (archetypes)
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        intids = getUtility(IIntIds)
        model = api.content.create(self.portal, type='File',
                                   id='invoice_model',
                                   file=BlobbableFile(open(TEST_INVOICE_ODT)),
                                   )

        content = api.content.create(self.portal, type='invoice',
                           title=u"Invoice for the Great Company intranet",
                           bill_date=datetime.date(2012, 12, 23),
                           customer="The Great company",
                           order_num='12A',
                           vat_excluded=1000.0,
                           vat=0.19,
                           vat_included=1190.0,
                           relatedItems=[RelationValue(intids.getId(model))],
                           )

        content.unrestrictedTraverse('@@documentfusion-refresh')()
        notify(ObjectModifiedEvent(content))

        generated_stream = content.unrestrictedTraverse('@@getdocumentfusion')()
        self.assertTrue(generated_stream)
        self.assertEqual(self.portal.REQUEST.response['content-type'],
                         'application/pdf')
        generated_path = tempfile.mktemp(suffix='invoice.pdf')
        generated_file = open(generated_path, 'w')
        generated_file.write(generated_stream.read())
        generated_file.close()

        txt_path = tempfile.mktemp(suffix='invoice.pdf')
        subprocess.call(['pdftotext', generated_path, txt_path])
        txt = open(txt_path).read()
        self.assertIn('2012', txt)
        self.assertIn('12A', txt)
        self.assertIn('1 000,00 €', txt)
        self.assertIn('19,00%', txt)
        os.remove(txt_path)
        os.remove(generated_path)
