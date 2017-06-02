# -*- coding: utf-8 -*-
"""Setup/installation tests for this package."""

import os
import datetime
import tempfile
import subprocess

from plone.uuid.interfaces import IUUID
from zope.component import getMultiAdapter
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
from collective.documentfusion.interfaces import ICollectiveDocumentfusionLayer, IModelFileSource, IFusionData, IMergeDataSources
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

    def test_named_source(self):
        request = self.portal.REQUEST
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        content = api.content.create(self.portal, type='letter',
                                     title=u"En réponse...",
                                     file=NamedFile(data=open(TEST_LETTER_ODT).read(),
                                                    filename=u'letter.odt',
                                                    contentType='application/vnd.oasis.opendocument.text'),
                                     sender_name="Thomas Desvenain",
                                     sender_address="573 Quai de Turenne",
                                     recipient_name="Vincent Fretin",
                                     date=datetime.date(2012, 12, 23))
        model = getMultiAdapter((content, content.REQUEST), IModelFileSource, name='')()
        self.assertEqual(model.filename, 'letter.odt')

    def test_fusion_data(self):
        content = api.content.create(self.portal, type='letter',
                                     title=u"En réponse...",
                                     file=NamedFile(data=open(TEST_LETTER_ODT).read(),
                                                    filename=u'letter.odt',
                                                    contentType='application/vnd.oasis.opendocument.text'),
                                     sender_name="Thomas Desvenain",
                                     sender_address="573 Quai de Turenne",
                                     recipient_name="Vincent Fretin",
                                     date=datetime.date(2012, 12, 23))
        fusion_data = getMultiAdapter((content, content.REQUEST), IFusionData, name='')()
        expected_fusion_data = {
            'Author': 'test_user_1_',
            'Title': u"En réponse...",
            'date': '2012-12-23',
            'description': '',
            'document_id': 'en-reponse',
            'file': u'letter.odt',
            'language': '',
            'path': '/plone/en-reponse',
            'recipient_address': None,
            'recipient_name': 'Vincent Fretin',
            'sender_address': '573 Quai de Turenne',
            'sender_name': 'Thomas Desvenain',
            'subjects': u'',
            'title': u"En réponse...",
            'uid': IUUID(content),
            'url': 'http://nohost/plone/en-reponse'
        }
        self.assertEqual(fusion_data, expected_fusion_data)

    def test_collection_source(self):
        # data source is in a related content
        # we merge two files from two sources
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        intids = getUtility(IIntIds)
        source_1 = api.content.create(self.portal, type='contact_infos',
                                      id='desvenain_thomas')

        source_2 = api.content.create(self.portal, type='contact_infos',
                                      id='fretin_vincent')

        content = api.content.create(self.portal, type='label_model',
                                     title=u"Modèle d'étiquette",
                                     file=NamedFile(data=open(TEST_LABEL_ODT).read(),
                                                    filename=u'label.odt',
                                                    contentType='application/vnd.oasis.opendocument.text'),
                                     relatedItems=[RelationValue(intids.getId(source_1)),
                                                   RelationValue(intids.getId(source_2))],
                                     )

        content_collection = getMultiAdapter((content, content.REQUEST), IMergeDataSources, name='')()
        self.assertItemsEqual(content_collection, [source_1, source_2])

    def test_document_fusion(self):
        # data source and model are in the same content
        alsoProvides(self.portal.REQUEST, ICollectiveDocumentfusionLayer)
        content = api.content.create(self.portal, type='letter',
                                     title=u"En réponse...",
                                     file=NamedFile(data=open(TEST_LETTER_ODT).read(),
                                                    filename=u'letter.odt',
                                                    contentType='application/vnd.oasis.opendocument.text'),
                                     sender_name="Thomas Desvenain",
                                     sender_address="573 Quai de Turenne",
                                     recipient_name="Vincent Fretin",
                                     date=datetime.date(2012, 12, 23))

        notify(ObjectModifiedEvent(content))

        annotations = IAnnotations(content)
        status = annotations.get(STATUS_STORAGE_KEY, None)
        self.assertEqual(status, TASK_SUCCEEDED)

        generated_stream = content.unrestrictedTraverse('@@download-documentfusion')()
        self.assertTrue(generated_stream)
        self.assertEqual(self.portal.REQUEST.response['content-type'],
                         'application/pdf')
        generated_path = tempfile.mktemp(suffix='letter.pdf')
        generated_file = open(generated_path, 'w')
        generated_file.write(generated_stream.read())
        generated_file.close()

        txt_path = tempfile.mktemp(suffix='letter.pdf')
        subprocess.call(['pdftotext', generated_path, txt_path])
        txt = open(txt_path).read().replace(r'\xc2\xa0', ' ')
        self.assertIn('Vincent Fretin', txt)
        self.assertIn('573 Quai de Turenne', txt)
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

        generated_stream = content.unrestrictedTraverse('@@download-documentfusion')()
        self.assertTrue(generated_stream)
        self.assertEqual(self.portal.REQUEST.response['content-type'],
                         'application/pdf')
        generated_path = tempfile.mktemp(suffix='label.pdf')
        generated_file = open(generated_path, 'w')
        generated_file.write(generated_stream.read())
        generated_file.close()

        txt_path = tempfile.mktemp(suffix='label.pdf')
        subprocess.call(['pdftotext', generated_path, txt_path])
        txt = open(txt_path).read().replace(r'\xc2\xa0', ' ')
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

        generated_stream = content.unrestrictedTraverse('@@download-documentfusion')()
        self.assertTrue(generated_stream)
        self.assertEqual(self.portal.REQUEST.response['content-type'],
                         'application/pdf')
        generated_path = tempfile.mktemp(suffix='label.pdf')
        generated_file = open(generated_path, 'w')
        generated_file.write(generated_stream.read())
        generated_file.close()

        txt_path = tempfile.mktemp(suffix='label.pdf')
        subprocess.call(['pdftotext', generated_path, txt_path])
        txt = open(txt_path).read().replace(r'\xc2\xa0', ' ')

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

        generated_stream = content.unrestrictedTraverse('@@download-documentfusion')()
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

        content.unrestrictedTraverse('@@refresh-documentfusion')()
        notify(ObjectModifiedEvent(content))

        generated_stream = content.unrestrictedTraverse('@@download-documentfusion')()
        self.assertTrue(generated_stream)
        self.assertEqual(self.portal.REQUEST.response['content-type'], 'application/pdf')
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
