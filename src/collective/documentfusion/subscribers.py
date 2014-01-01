from collective.documentfusion.interfaces import (
        IDocumentFusion, IPDFGeneration, IMergeDocumentFusion)
from collective.documentfusion.converter import convert_document, merge_document


def pdf_generation(obj, event):
    if IDocumentFusion.providedBy(obj):
        return

    convert_document(obj, make_fusion=False, target_extension='pdf')


def document_fusion(obj, event):
    if IMergeDocumentFusion.providedBy(obj):
        return

    if IPDFGeneration.providedBy(obj):
        convert_document(obj, make_fusion=True, target_extension='pdf')
    else:
        convert_document(obj, make_fusion=True, target_extension=None)


def merge_document_fusion(obj, event):
    merge_document(obj)
