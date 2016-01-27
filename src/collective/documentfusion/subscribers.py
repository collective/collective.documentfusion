from collective.documentfusion.interfaces import (
    IDocumentFusion, IPDFGeneration, IMergeDocumentFusion)
from collective.documentfusion.converter import convert_document, merge_document


def refresh(obj, event=None):
    if IMergeDocumentFusion.providedBy(obj):
        return merge_document(obj)

    # target_extension = IPDFGeneration.providedBy(obj) and 'pdf' or None
    target_extension = 'odt'
    make_fusion = IDocumentFusion.providedBy(obj)
    convert_document(obj, make_fusion=make_fusion, target_extension=target_extension)
