from collective.documentfusion.interfaces import IDocumentFusion, IPDFGeneration
from collective.documentfusion.converter import convert_document
from collective.documentfusion.interfaces import IMultipleDocumentFusion

from collective.documentfusion import logger

def pdf_generation(obj, event):
    if IDocumentFusion.providedBy(obj):
        return

    convert_document(obj, make_fusion=False, target_extension='pdf')


def document_fusion(obj, event):
    if IMultipleDocumentFusion.providedBy(obj):
        logger.error("We can use IMultipleDocumentFusion AND IDocumentFusion."
                     "  only IMultipleDocumentFusion will be used.")
    if IPDFGeneration.providedBy(obj):
        convert_document(obj, make_fusion=True, target_extension='pdf')
    else:
        convert_document(obj, make_fusion=True, target_extension=None)


def multiple_document_fusion(obj, event):
    if IPDFGeneration.providedBy(obj):
        convert_document(obj, make_fusion=True,
                         target_extension='pdf', use_external_sources=True)
    else:
        convert_document(obj, make_fusion=True, target_extension=None,
                         use_external_sources=True)