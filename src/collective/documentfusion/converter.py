import os
import tempfile
import logging

from PyODConverter import EXPORT_FILTER_MAP, DocumentConverter

from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from plone.namedfile.file import NamedBlobFile
from plone.app.blob.utils import guessMimetype

from collective.documentfusion.interfaces import (
    IFusionData, ISourceFile, IMultipleFusionSources,\
    TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED,
    DATA_STORAGE_KEY, STATUS_STORAGE_KEY)

logger = logging.getLogger('collective.documentfusion.converter')


def filename_split(filename):
    return filename.rsplit('.', 1)


def convert_document(obj, target_extension=None,
                     make_fusion=False, use_external_sources=False):
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
        if use_external_sources:
            external_fusion_sources = getMultiAdapter((obj, obj.REQUEST),
                                                      IMultipleFusionSources)()
            if len(external_fusion_sources) == 1:
                fusion_data.update(getMultiAdapter((external_fusion_sources[0],
                                                    obj.REQUEST), IFusionData)()
                                   )
            elif len(external_fusion_sources) == 0:
                pass
            else:
                raise NotImplemented
    else:
        fusion_data = None

    converted_file = get_converted_file(named_file,
                                        target_extension,
                                        fusion_data,
                                        )
    if converted_file is None:
        annotations[STATUS_STORAGE_KEY] = TASK_FAILED
        annotations[DATA_STORAGE_KEY] = None
    else:
        annotations[STATUS_STORAGE_KEY] = TASK_SUCCEEDED
        annotations[DATA_STORAGE_KEY] = converted_file


def get_converted_file(named_file, target_ext, fusion_data, tmp_dir='/tmp'):
    """Get a converted file in a blob file
    from source named file, with target extension and fusion data as a dict.
    """
    filename = named_file.filename
    tmp_source_file_path = tempfile.mktemp(
                                suffix='--%s' % filename)
    tmp_source_file = open(tmp_source_file_path, 'w')
    tmp_source_file.write(named_file.data)
    tmp_source_file.close()
    base_filename = filename_split(filename)[0]
    tmp_converted_file_path = tempfile.mktemp(
                                suffix='--%s.%s' % (base_filename, target_ext))

    DocumentConverter().convert(tmp_source_file_path,
                                tmp_converted_file_path,
                                data=fusion_data)

    converted_file = open(tmp_converted_file_path)
    converted_file_name = os.path.split(tmp_converted_file_path)[-1].split('--')[-1]
    converted_file_mimetype = guessMimetype(converted_file, filename=converted_file_name)
    converted_file_blob = NamedBlobFile(data=converted_file.read(),
                                        contentType=converted_file_mimetype,
                                        filename=unicode(converted_file_name))
    os.remove(tmp_source_file_path)
    os.remove(tmp_converted_file_path)
    return converted_file_blob
