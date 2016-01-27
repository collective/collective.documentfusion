import traceback
import os
import tempfile
import logging

import requests
import json
from PyPDF2 import PdfFileMerger, PdfFileReader

from DateTime import DateTime
from zope.component import getUtility, getMultiAdapter
from zope.component.interfaces import ComponentLookupError
from zope.annotation.interfaces import IAnnotations

from plone.registry.interfaces import IRegistry
from plone.namedfile.file import NamedBlobFile
from plone.app.blob.utils import guessMimetype

from collective.documentfusion.interfaces import (
    ISOfficeSettings,
    IFusionData, IModelFileSource, IMergeDataSources,
    TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED,
    DATA_STORAGE_KEY, STATUS_STORAGE_KEY)

logger = logging.getLogger('collective.documentfusion.converter')


def filename_split(filename):
    return filename.rsplit('.', 1)


def _store_namedfile_in_fs_temp(named_file):
    fs_path = tempfile.mktemp(suffix='--%s' % named_file.filename)
    file_obj = open(fs_path, 'w')
    file_obj.write(named_file.data)
    file_obj.close()
    assert os.path.exists(fs_path)
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
    # section of convert_document process that should be run asyncronously
    converted_file = get_converted_file(
        named_file,
        target_extension,
        fusion_data,
    )
    annotations = IAnnotations(obj)
    previous_status = annotations[STATUS_STORAGE_KEY]
    if converted_file is None:
        new_status = TASK_FAILED
        annotations[DATA_STORAGE_KEY] = None
    else:
        new_status = TASK_SUCCEEDED
        annotations[DATA_STORAGE_KEY] = converted_file

    annotations[STATUS_STORAGE_KEY] = new_status
    if new_status != previous_status:
        obj.setModificationDate(DateTime())

    # @TODO: refresh etag


def convert_document(obj, target_extension=None, make_fusion=False):
    """We store in an annotation the conversion of the model file
       into the target extension
       eventually filled with data get from a source
       if we have many sources, we get a merge of this document filled with all
       sources
    """
    annotations = IAnnotations(obj)
    annotations[DATA_STORAGE_KEY] = None
    annotations[STATUS_STORAGE_KEY] = TASK_IN_PROGRESS
    named_file = getMultiAdapter((obj, obj.REQUEST), IModelFileSource)()
    source_extension = filename_split(named_file.filename)[1]

    if not target_extension:
        target_extension = source_extension

    if make_fusion:
        fusion_data = getMultiAdapter((obj, obj.REQUEST), IFusionData)()
    else:
        fusion_data = None

    try:
        from plone.app.async.interfaces import IAsyncService
        async = getUtility(IAsyncService)
        async.queueJob(__convert_document, obj, named_file,
                       target_extension, fusion_data)
    except (ImportError, ComponentLookupError):
        __convert_document(obj, named_file, target_extension, fusion_data)


def __merge_document(obj, named_file, fusion_data_list):
    # section of merge_document process that should be run asyncronously
    annotations = IAnnotations(obj)
    merged_file = get_merged_file(named_file, fusion_data_list)
    if merged_file is None:
        annotations[STATUS_STORAGE_KEY] = TASK_FAILED
        annotations[DATA_STORAGE_KEY] = None
    else:
        annotations[STATUS_STORAGE_KEY] = TASK_SUCCEEDED
        annotations[DATA_STORAGE_KEY] = merged_file

    # @TODO: refresh etag


def merge_document(obj):
    """We store in an annotation a pdf file
       wich merges a fusion of model
       filled with data get from a source
       if we have many sources, we get a merge of this document filled with all
       sources
    """
    annotations = IAnnotations(obj)
    annotations[DATA_STORAGE_KEY] = None
    annotations[STATUS_STORAGE_KEY] = TASK_IN_PROGRESS
    named_file = getMultiAdapter((obj, obj.REQUEST), IModelFileSource)()

    external_fusion_sources = getMultiAdapter((obj, obj.REQUEST),
                                              IMergeDataSources)()

    fusion_data_list = [getMultiAdapter((source, obj.REQUEST), IFusionData)()
        for source in external_fusion_sources]

    try:
        from plone.app.async.interfaces import IAsyncService
        async = getUtility(IAsyncService)
        async.queueJob(__merge_document, obj, named_file, fusion_data_list)
    except (ImportError, ComponentLookupError):
        __merge_document(obj, named_file, fusion_data_list)


def convert_file(tmp_source_file_path, tmp_converted_file_path, target_ext,
                 fusion_data=None):
    """Uses PyODConverted to convert a file into an other format
    filling properties, bookmarks and fields with data
    using libreoffice service
    """
    settings = getUtility(IRegistry).forInterface(ISOfficeSettings)
    files = {
        'tmpl_file': open(tmp_source_file_path, 'rb')
    }
    if not fusion_data:
        fusion_data = {}
    else:
        fusion_data = {'document': fusion_data}
    fields = {
        "targetformat": target_ext,
        "datadict": json.dumps(fusion_data),
        "image_mapping": "{}",
    }
    req = requests.post(
        "http://%s:%s/form" % (settings.host, settings.port),
        data=fields,
        files=files,
    )
    if req.status_code != 400:
        chunk_size = 1024
        with open(tmp_converted_file_path, 'wb') as fd:
            for chunk in req.iter_content(chunk_size):
                fd.write(chunk)
    else:
        raise Exception("py3o.fusion server error")

    assert os.path.exists(tmp_converted_file_path)


def merge_pdfs(source_file_pathes,
               merge_file_path):
    """Merge a list of source files into a new file using uno and libreoffice
    """

    merger = PdfFileMerger()
    for source_file_path in source_file_pathes:
        merger.append(PdfFileReader(open(source_file_path, 'rb')))

    merger.write(str(merge_file_path))


def get_converted_file(named_file, target_ext, fusion_data):
    """Get a converted file in a blob file
    from source named file, with target extension and fusion data as a dict.
    """
    tmp_source_file_path = _store_namedfile_in_fs_temp(named_file)

    suffix = '--%s.%s' % (filename_split(named_file.filename)[0], target_ext)
    tmp_converted_file_path = tempfile.mktemp(suffix=suffix)

    try:
        convert_file(
            tmp_source_file_path,
            tmp_converted_file_path,
            target_ext,
            fusion_data
        )
    except Exception:
        logger.error(traceback.format_exc())
        return None

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
        convert_file(
            tmp_source_file_path,
            tmp_converted_subfile_path,
            'pdf',
            fusion_data
        )
        converted_subfile_pathes.append(tmp_converted_subfile_path)

    # merge all fusion files
    suffix = '--%s.pdf' % (base_filename,)
    tmp_merged_file_path = tempfile.mktemp(suffix=suffix)
    # @TODO: cropping ?
    merge_pdfs(converted_subfile_pathes, tmp_merged_file_path)

    # get blob
    merged_file_blob = _get_blob_from_fs_file(tmp_merged_file_path)

    # cleanup
    os.remove(tmp_source_file_path)
    os.remove(tmp_merged_file_path)
    for fs_path in converted_subfile_pathes:
        os.remove(fs_path)

    return merged_file_blob
