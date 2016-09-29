import os
import tempfile
import logging

import requests
from collective.documentfusion.exceptions import Py3oException
from requests.exceptions import ConnectionError
import json
from PyPDF2 import PdfFileMerger, PdfFileReader

from DateTime import DateTime

from zope.component import getUtility, getMultiAdapter
from zope.component.interfaces import ComponentLookupError

from plone.registry.interfaces import IRegistry
from plone.namedfile.file import NamedBlobFile
from plone.app.blob.utils import guessMimetype

from collective.documentfusion.interfaces import (
    ISOfficeSettings, IFusionStorage,
    IFusionData, IModelFileSource, IMergeDataSources,
    TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED, IMergeDocumentFusion,
    IPDFGeneration,
    IDocumentFusion, IFusionDataReducer)

logger = logging.getLogger('collective.documentfusion.converter')


def filename_split(filename):
    return filename.rsplit('.', 1)


def remove_if_exists(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)


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


def __convert_document(obj, named_file, target_extension, fusion_data,
                       conversion_name=''):
    # section of convert_document process that should be run asyncronously
    storage = IFusionStorage(obj)
    try:
        converted_file = get_converted_file(
            named_file,
            target_extension,
            fusion_data,
        )
    except Exception, e:
        storage.set_status(TASK_FAILED, conversion_name)
        storage.set_file(None, conversion_name)
        logger.exception(str(e))
    else:
        previous_status = storage.get_status(conversion_name)
        if converted_file is None:
            new_status = TASK_FAILED
            storage.set_file(None, conversion_name)
        else:
            new_status = TASK_SUCCEEDED
            storage.set_file(converted_file, conversion_name)

        storage.set_status(new_status, conversion_name)
        if new_status != previous_status:
            obj.setModificationDate(DateTime())

            # @TODO: refresh etag


def convert_document(obj, target_extension=None, make_fusion=False,
                     conversion_name=''):
    """We store in an annotation the conversion of the model file
       into the target extension
       eventually filled with data get from a source
       if we have many sources, we get a merge of this document filled with all
       sources
    """
    storage = IFusionStorage(obj)
    storage.set_file(None, conversion_name)
    storage.set_status(TASK_IN_PROGRESS, conversion_name)

    named_file = getMultiAdapter((obj, obj.REQUEST), IModelFileSource,
                                 name=conversion_name)()
    source_extension = filename_split(named_file.filename)[1]

    if not target_extension:
        target_extension = source_extension

    if make_fusion:
        fusion_data = getMultiAdapter((obj, obj.REQUEST), IFusionData,
                                      name=conversion_name)()
    else:
        fusion_data = None

    try:
        from plone.app.async.interfaces import IAsyncService
        async = getUtility(IAsyncService)
        async.queueJob(__convert_document, obj, named_file,
                       target_extension, fusion_data, conversion_name)
    except (ImportError, ComponentLookupError):
        __convert_document(obj, named_file, target_extension, fusion_data,
                           conversion_name=conversion_name)


def __merge_document(obj, named_file, fusion_data_list, conversion_name=''):
    # section of merge_document process that should be run asynchronously
    storage = IFusionStorage(obj)
    try:
        merged_file = get_merged_file(named_file, fusion_data_list)
    except Exception, e:
        storage.set_status(TASK_FAILED, conversion_name)
        storage.set_file(None, conversion_name)
        logger.exception(str(e))
    else:
        if merged_file is None:
            storage.set_status(TASK_FAILED, conversion_name)
            storage.set_file(None, conversion_name)
        else:
            storage.set_status(TASK_SUCCEEDED, conversion_name)
            storage.set_file(merged_file, conversion_name)

        # @TODO: refresh etag


def merge_document(obj, conversion_name=''):
    """We store in an annotation a pdf file
       wich merges a fusion of model
       filled with data get from a source
       if we have many sources, we get a merge of this document filled with all
       sources
    """
    storage = IFusionStorage(obj)
    storage.set_file(None, conversion_name)
    storage.set_status(TASK_IN_PROGRESS, conversion_name)

    # get source file
    named_file = getMultiAdapter((obj, obj.REQUEST), IModelFileSource,
                                 name=conversion_name)()

    # get contents from which we get data
    external_fusion_sources = getMultiAdapter((obj, obj.REQUEST),
                                              IMergeDataSources,
                                              name=conversion_name)()

    try:
        # consolidate data if any reducer is provided (not by default)
        reducer = getMultiAdapter((obj, obj.REQUEST),
                                  IFusionDataReducer,
                                  name=conversion_name)

        fusion_data_list = reduce(
            lambda c, v: (c[0] + 1, reducer(c[1], c[0], v)),
            external_fusion_sources,
            (0, []))[1]
    except ComponentLookupError:
        # if no reducer is provided, just get data from those contents in a list
        fusion_data_list = (getMultiAdapter((source, obj.REQUEST), IFusionData,
                                            name=conversion_name)()
                            for source in external_fusion_sources)
        pass

    try:
        from plone.app.async.interfaces import IAsyncService
        async = getUtility(IAsyncService)
        async.queueJob(__merge_document, obj, named_file, fusion_data_list,
                       conversion_name=conversion_name)
    except (ImportError, ComponentLookupError):
        __merge_document(obj, named_file, fusion_data_list,
                         conversion_name=conversion_name)


def convert_file(tmp_source_file_path, tmp_converted_file_path, target_ext,
                 fusion_data=None):
    """Uses py3o to convert a file into an other format
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
        files=files
    )
    if req.status_code != 400:
        chunk_size = 1024
        with open(tmp_converted_file_path, 'wb') as fd:
            for chunk in req.iter_content(chunk_size):
                fd.write(chunk)
    else:
        raise Py3oException("py3o.fusion server error: %s", req.text)

    assert os.path.exists(tmp_converted_file_path)


def merge_pdfs(source_file_pathes, merge_file_path):
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
        return _get_blob_from_fs_file(tmp_converted_file_path)
    finally:
        remove_if_exists(tmp_source_file_path)
        remove_if_exists(tmp_converted_file_path)


def get_merged_file(named_file, fusion_data_list):
    """Get a merged pdf file in a blob file
    from source named file, with target extension
    and the list of data dictionaries for fusion.
    """
    tmp_source_file_path = _store_namedfile_in_fs_temp(named_file)
    converted_subfile_pathes = []
    base_filename = filename_split(named_file.filename)[0]
    suffix = '--%s.pdf' % (base_filename,)
    tmp_merged_file_path = tempfile.mktemp(suffix=suffix)
    try:
        # create a fusion from each data source
        for num, fusion_data in enumerate(fusion_data_list):
            suffix = '--%s-%s.pdf' % (num, base_filename)
            tmp_converted_subfile_path = tempfile.mktemp(suffix=suffix)
            try:
                convert_file(
                    tmp_source_file_path,
                    tmp_converted_subfile_path,
                    'pdf',
                    fusion_data
                )
            except:
                remove_if_exists(tmp_converted_subfile_path)
                raise

            converted_subfile_pathes.append(tmp_converted_subfile_path)

        # merge all fusion files
        # @TODO: cropping ?
        merge_pdfs(converted_subfile_pathes, tmp_merged_file_path)

        # get blob
        merged_file_blob = _get_blob_from_fs_file(tmp_merged_file_path)
        return merged_file_blob
    finally:
        # cleanup
        remove_if_exists(tmp_source_file_path)
        remove_if_exists(tmp_merged_file_path)
        for fs_path in converted_subfile_pathes:
            remove_if_exists(fs_path)


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
