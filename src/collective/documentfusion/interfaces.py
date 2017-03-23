# -*- coding: utf-8 -*-
"""Module where all interfaces, events and exceptions live."""
from zope.schema import ASCIILine, Bool, Int
from zope.component import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from collective.documentfusion import _

TASK_SUCCEEDED = 'success'
TASK_IN_PROGRESS = 'in_progress'
TASK_FAILED = 'failed'

DATA_STORAGE_KEY = 'collective.documentfusion.file'
STATUS_STORAGE_KEY = 'collective.documentfusion.status'

PREVENT_REFRESH_KEY = 'collective.documentfusion.prevent-refresh'

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


class IImageMapping(Interface):
    """Adapter which provides the image mapping of a content.
    Adapts object and request.
    """


class IMergeDataSources(Interface):
    """Adapter which provides the source contents for the document merge
    from the main document.
    """


class IFusionDataReducer(Interface):
    """Adapter which reduces fusionned data during a merge document fusion
    """

    def __call__(self, reduced, content_index, content):
        """

        @param reduced: list -> result of previous step
        @param content_index: int -> index of content currently handled
        @param content_data: dic -> data of current content
        @return: list
        """


class IFusionStorage(Interface):
    """Adapter to ease access to stored information
    """

    def get_status(self, conversion_name=''):
        """Get conversion status: success, failure or pending.
        """

    def set_status(self, status, conversion_name=''):
        """Set conversion status.
        """

    def get_file(self, conversion_name=''):
        """Get converted file.
        """

    def set_file(self, named_file, conversion_name=''):
        """Set converted file.
        """


class ISettings(Interface):
    fusion_service_port = Int(
        title=_(u"Fusion service port"),
        description=_(u"The port used by py3o.fusion service"),
    )

    fusion_service_host = ASCIILine(
        title=_(u"Fusion service host"),
        description=_(u"The hostname from where py3o.fusion is served"),
    )

    fusion_timeout = Int(
        title=_(u"Fusion service timeout",),
        description=_(u"The maximum time (in seconds) the worker will wait for py3o.fusion service response.")
    )

    auto_refresh_enabled = Bool(
        title=_(u"Automatic refresh enabled"),
        description=_(u"Automatic refresh of generated files is enabled"),
    )

    disable_async = Bool(
        title=_(u"Prevent using async document generation"),
        description=_(u"For development or test mode"),
    )
