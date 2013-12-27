from collective.documentfusion.interfaces import IDocumentFusion, IPDFGeneration
from collective.documentfusion.converter import convert_document


def pdf_generation(obj, event):
    if IDocumentFusion.providedBy(obj):
        return

    convert_document(obj, fusion=False, target_ext='pdf')


def document_fusion(obj, event):
    if IPDFGeneration.providedBy(obj):
        convert_document(obj, fusion=True, target_ext='pdf')
    else:
        convert_document(obj, fusion=True, target_ext=None)