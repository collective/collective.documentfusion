# -*- coding: utf-8 -*-
"""Module where all interfaces, events and exceptions live."""
from zope.schema import ASCIILine, Int
from zope.component import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from collective.documentfusion import _

TASK_SUCCEEDED = 'success'
TASK_IN_PROGRESS = 'in_progress'
TASK_FAILED = 'failed'

DATA_STORAGE_KEY = 'collective.documentfusion.file'
STATUS_STORAGE_KEY = 'collective.documentfusion.status'


class ICollectiveDocumentfusionLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class IGeneration(Interface):
    """
    """

class IPDFGeneration(IGeneration):
    """When this behavior is selected, we generate a pdf version
    of the main file of the document.
    """

class IDocumentFusion(IGeneration):
    """When this behavior is selected, we generate a fusion of the main file
    of the document with the fields of the dexterity content.
    """

class IMergeDocumentFusion(IDocumentFusion):
    """We generate a pdf
       that provides the merge of the model
       filled with fields of each document related items
    """

class IModelFileSource(Interface):
    """Adapter which provides the model file of a content for fusion.
    Adapts object and request.
    """

class IFusionData(Interface):
    """Adapter which provides the fusion data of a content.
    Adapts object and request.
    """

class IMergeDataSources(Interface):
    """Adapter which provides the source contents for the document merge
    from the main document.
    """

class ISOfficeSettings(Interface):

    port = ASCIILine(title=_(u"LibreOffice port"),
                    description=_(u"The port used by LibreOffice service"))

    host = Int(title=_(u"LibreOffice host"),
               description=_(u"The port used by LibreOffice service"))
