from collective.documentfusion.interfaces import (
    IMergeDataSources,
    IMergeDocumentFusion,
    IPDFGeneration,
    IDocumentFusion, IFusionData)
from conversion import convert_document
from pdfmerge import merge_document
from zope.component import queryMultiAdapter


def refresh_conversion(obj, conversion_name=None, make_pdf=None):
    """Update the conversion stored for the given content object
       If no conversion_name is given, we refresh default conversion with behavior settings
       @param obj: Object.           The source object of the document
       @param conversion_name: str.  The identifier of the conversion
       @param make_pdf: bool         Force pdf output
    """
    if conversion_name is None:
        conversion_name = ''
        do_merge = IMergeDocumentFusion.providedBy(obj)
        if make_pdf is None:
            target_extension = 'pdf' if IPDFGeneration.providedBy(obj) else None
        else:
            target_extension = 'pdf' if make_pdf else None
        do_make_fusion = IDocumentFusion.providedBy(obj)
    else:
        do_merge = bool(queryMultiAdapter((obj, obj.REQUEST), IMergeDataSources, name=conversion_name))
        do_make_fusion = bool(queryMultiAdapter((obj, obj.REQUEST), IFusionData, name=conversion_name))
        target_extension = 'pdf' if make_pdf else None

    if do_merge:
        merge_document(obj, conversion_name=conversion_name)
    else:
        convert_document(obj,
                         conversion_name=conversion_name,
                         make_fusion=do_make_fusion,
                         target_extension=target_extension)
