from collective.documentfusion.interfaces import (
    IMergeDataSources,
    IMergeDocumentFusion,
    IPDFGeneration,
    IDocumentFusion)
from conversion import convert_document
from pdfmerge import merge_document
from zope.component import getMultiAdapter
from zope.component.interfaces import ComponentLookupError


def refresh_conversion(obj):
    """Update the conversion stored for the object
    """
    if IMergeDocumentFusion.providedBy(obj):
        return merge_document(obj)

    target_extension = IPDFGeneration.providedBy(obj) and 'pdf' or None
    make_fusion = IDocumentFusion.providedBy(obj)
    convert_document(obj,
                     make_fusion=make_fusion,
                     target_extension=target_extension)


def apply_specific_conversion(obj, conversion_name, make_pdf=False):
    """Update the named conversion stored for the object,
    forcing pdf if you need so
    """
    try:
        getMultiAdapter((obj, obj.REQUEST), IMergeDataSources,
                        name=conversion_name)
    except ComponentLookupError:
        pass
    else:
        return merge_document(obj, conversion_name=conversion_name)

    target_extension = make_pdf and 'pdf' or None
    convert_document(obj, conversion_name=conversion_name, make_fusion=True,
                     target_extension=target_extension)
