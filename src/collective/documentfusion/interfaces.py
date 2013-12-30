# -*- coding: utf-8 -*-
"""Module where all interfaces, events and exceptions live."""
from zope.component import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


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

class IMultipleDocumentFusion(IGeneration):
    """We generate a fusion of the file field of the document
       with the field of document related items
       - and if fields are missing, with the fields of the document itself.
    """

class ISourceFile(Interface):
    """Adapter wich provides the source file of a content for fusion
    adapts object and request
    """

class IFusionData(Interface):
    """Adapter wich provides the fusion data of a content
    adapts object and request
    """

class IMultipleFusionSources(Interface):
    """Adapter wich provides the source contents for the multiple document fusion
    from the main document
    """