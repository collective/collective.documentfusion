import os
import tempfile
import logging

from PyODConverter import EXPORT_FILTER_MAP, DocumentConverter
from PyPDF2 import PdfFileMerger, PdfFileReader

from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from plone.namedfile.file import NamedBlobFile
from plone.app.blob.utils import guessMimetype

from collective.documentfusion.interfaces import (
    IFusionData, ISourceFile, IMergeDataSources,\
    TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED,
    DATA_STORAGE_KEY, STATUS_STORAGE_KEY)
from zope.component._api import getUtility
from plone.app.async.interfaces import IAsyncService

logger = logging.getLogger('collective.documentfusion.converter')


def filename_split(filename):
    return filename.rsplit('.', 1)


def _store_namedfile_in_fs_temp(named_file):
    fs_path = tempfile.mktemp(
                                suffix='--%s' % named_file.filename)
    file_obj = open(fs_path, 'w')
    file_obj.write(named_file.data)
    file_obj.close()
    return fs_path


def _get_blob_from_fs_file(file_path):
    """get blob file from fs file. remove tmp prefix separated by --
    """
    file_obj = open(file_path)
    file_name = os.path.split(file_path)[-1].split('--')[-1]
    file_mimetype = guessMimetype(file_obj, filename=file_name)
    file_blob = NamedBlobFile(data=file_obj.read(),
                              contentType=file_mimetype,
                              filename=unicode(file_name))
    return file_blob


def __convert_document(obj, named_file, target_extension, fusion_data):
    converted_file = get_converted_file(named_file,
                                    target_extension,
                                    fusion_data,
                                    )

    annotations = IAnnotations(obj)
    if converted_file is None:
        annotations[STATUS_STORAGE_KEY] = TASK_FAILED
        annotations[DATA_STORAGE_KEY] = None
    else:
        annotations[STATUS_STORAGE_KEY] = TASK_SUCCEEDED
        annotations[DATA_STORAGE_KEY] = converted_file


def convert_document(obj, target_extension=None, make_fusion=False):
    """We store in an annotation the conversion of the model file
       into the target extension
       eventually filled with data get from a source
       if we have many sources, we get a merge of this document filled with all sources
    """
    annotations = IAnnotations(obj)
    annotations[DATA_STORAGE_KEY] = None
    annotations[STATUS_STORAGE_KEY] = TASK_IN_PROGRESS
    named_file = getMultiAdapter((obj, obj.REQUEST), ISourceFile)()
    source_extension = filename_split(named_file.filename)[1]
    if source_extension not in EXPORT_FILTER_MAP:
        return

    if not target_extension:
        target_extension = source_extension

    if make_fusion:
        fusion_data = getMultiAdapter((obj, obj.REQUEST), IFusionData)()
    else:
        fusion_data = None

    async = getUtility(IAsyncService)
    async.queueJob(__convert_document, obj, named_file, target_extension, fusion_data)


def __merge_document(obj, named_file, fusion_data_list):
    annotations = IAnnotations(obj)
    merged_file = get_merged_file(named_file, fusion_data_list)
    if merged_file is None:
        annotations[STATUS_STORAGE_KEY] = TASK_FAILED
        annotations[DATA_STORAGE_KEY] = None
    else:
        annotations[STATUS_STORAGE_KEY] = TASK_SUCCEEDED
        annotations[DATA_STORAGE_KEY] = merged_file


def merge_document(obj):
    """We store in an annotation a pdf file
       wich merges a fusion of model
       filled with data get from a source
       if we have many sources, we get a merge of this document filled with all sources
    """
    annotations = IAnnotations(obj)
    annotations[DATA_STORAGE_KEY] = None
    annotations[STATUS_STORAGE_KEY] = TASK_IN_PROGRESS
    named_file = getMultiAdapter((obj, obj.REQUEST), ISourceFile)()

    external_fusion_sources = getMultiAdapter((obj, obj.REQUEST),
                                              IMergeDataSources)()


    fusion_data_list = [getMultiAdapter((source, obj.REQUEST),
                                        IFusionData)()
                        for source in external_fusion_sources]

    async = getUtility(IAsyncService)
    async.queueJob(__merge_document, obj, named_file, fusion_data_list)


def convert_file(tmp_source_file_path, tmp_converted_file_path,
                 fusion_data=None):
    """Uses PyODConverted to convert a file into an other format
    filling properties, bookmarks and fields with data
    using libreoffice service
    """
    DocumentConverter().convert(tmp_source_file_path,
                                tmp_converted_file_path,
                                data=fusion_data)


def merge_pdfs(source_file_pathes,
               merge_file_path):
    """Merge a list of source files into a new file using uno and libreoffice
    """

    merger = PdfFileMerger()
    for source_file_path in source_file_pathes:
        merger.append(PdfFileReader(open(source_file_path, 'rb')))

    merger.write(merge_file_path)


def get_converted_file(named_file, target_ext, fusion_data):
    """Get a converted file in a blob file
    from source named file, with target extension and fusion data as a dict.
    """
    tmp_source_file_path = _store_namedfile_in_fs_temp(named_file)

    suffix = '--%s.%s' % (filename_split(named_file.filename)[0], target_ext)
    tmp_converted_file_path = tempfile.mktemp(suffix=suffix)

    convert_file(tmp_source_file_path, tmp_converted_file_path, fusion_data)

    converted_file_blob = _get_blob_from_fs_file(tmp_converted_file_path)

    os.remove(tmp_source_file_path)
    os.remove(tmp_converted_file_path)
    return converted_file_blob


def get_merged_file(named_file, fusion_data_list):
    """Get a merged pdf file in a blob file
    from source named file, with target extension
    and the list of data dictionaries for fusion.
    """
    tmp_source_file_path = _store_namedfile_in_fs_temp(named_file)
    converted_subfile_pathes = []
    base_filename = filename_split(named_file.filename)[0]
    # create a fusion from each data source
    for num, fusion_data in enumerate(fusion_data_list):
        suffix = '--%s-%s.pdf' % (num, base_filename)
        tmp_converted_subfile_path = tempfile.mktemp(suffix=suffix)
        convert_file(tmp_source_file_path, tmp_converted_subfile_path, fusion_data)
        converted_subfile_pathes.append(tmp_converted_subfile_path)

    # merge all fusion files
    suffix = '--%s.pdf' % (base_filename,)
    tmp_merged_file_path = tempfile.mktemp(suffix=suffix)
    merge_pdfs(converted_subfile_pathes, tmp_merged_file_path)

    # get blob
    merged_file_blob = _get_blob_from_fs_file(tmp_merged_file_path)

    # cleanup
    os.remove(tmp_source_file_path)
    os.remove(tmp_merged_file_path)
    for fs_path in converted_subfile_pathes:
        os.remove(fs_path)

    return merged_file_blob