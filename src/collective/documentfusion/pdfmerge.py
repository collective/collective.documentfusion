import logging
import tempfile

from PyPDF2 import PdfFileMerger, PdfFileReader
from collective.documentfusion.conversion import convert_fs_file
from collective.documentfusion.interfaces import (
    IFusionStorage,
    TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED)
from zope.component.interfaces import ComponentLookupError
from .utils import (
    execute_job,
    filename_split,
    get_blob_from_fs_file,
    remove_if_exists,
    store_namedfile_in_fs_temp,
    get_fusion_data, get_image_mapping, get_model_file_source,
    get_merge_data_sources, get_fusion_data_reducer)

logger = logging.getLogger('collective.documentfusion.pdfmerge')


def __merge_document(obj, named_file, fusion_data_list=None, image_mapping=None, conversion_name=''):
    # section of merge_document process that should be run asynchronously
    storage = IFusionStorage(obj)
    try:
        merged_file = get_merged_file(named_file, fusion_data_list=fusion_data_list, image_mapping=image_mapping)
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
    named_file = get_model_file_source(obj, obj.REQUEST,
                                       conversion_name=conversion_name)

    # get contents from which we get data
    external_fusion_sources = get_merge_data_sources(obj, obj.REQUEST,
                                                     conversion_name=conversion_name)

    try:
        # consolidate data if any reducer is provided (not by default)
        reducer = get_fusion_data_reducer(obj, obj.REQUEST,
                                          conversion_name=conversion_name)
        fusion_data_list = reduce(
            lambda c, v: (c[0] + 1, reducer(c[1], c[0], v)),
            external_fusion_sources,
            (0, []))[1]
    except ComponentLookupError:
        # if no reducer is provided, just get data from those contents in a list
        fusion_data_list = (get_fusion_data(source, obj.REQUEST,
                                            conversion_name=conversion_name)
                            for source in external_fusion_sources)

    image_mapping = get_image_mapping(obj, obj.REQUEST,
                                      conversion_name=conversion_name)

    execute_job(__merge_document,
                obj, named_file, fusion_data_list,
                image_mapping=image_mapping,
                conversion_name=conversion_name)


def merge_pdfs(source_file_pathes, merge_file_path):
    """Merge a list of source files into a new file using uno and libreoffice
    """
    merger = PdfFileMerger()
    for source_file_path in source_file_pathes:
        merger.append(PdfFileReader(open(source_file_path, 'rb')))

    merger.write(str(merge_file_path))


def get_merged_file(named_file, fusion_data_list, image_mapping=None):
    """Get a merged pdf file in a blob file
    from source named file, with target extension
    and the list of data dictionaries for fusion.
    """
    tmp_source_file_path = store_namedfile_in_fs_temp(named_file)
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
                convert_fs_file(
                    tmp_source_file_path,
                    tmp_converted_subfile_path,
                    'pdf',
                    fusion_data=fusion_data,
                    image_mapping=image_mapping
                )
            except:
                remove_if_exists(tmp_converted_subfile_path)
                raise

            converted_subfile_pathes.append(tmp_converted_subfile_path)

        # merge all fusion files
        # @TODO: cropping ?
        merge_pdfs(converted_subfile_pathes, tmp_merged_file_path)

        # get blob
        merged_file_blob = get_blob_from_fs_file(tmp_merged_file_path)
        return merged_file_blob
    finally:
        # cleanup
        remove_if_exists(tmp_source_file_path)
        remove_if_exists(tmp_merged_file_path)
        for fs_path in converted_subfile_pathes:
            remove_if_exists(fs_path)
