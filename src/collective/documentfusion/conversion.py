import json
import logging
import os
import tempfile

import requests
from DateTime import DateTime
from collective.documentfusion.exceptions import Py3oException
from collective.documentfusion.interfaces import (
    ISettings, IFusionStorage,
    IFusionData, IModelFileSource, TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED)
from plone.registry.interfaces import IRegistry
from zope.component import getUtility, getMultiAdapter
from .utils import (
    execute_job,
    filename_split,
    get_blob_from_fs_file,
    store_namedfile_in_fs_temp,
    remove_if_exists,
)


logger = logging.getLogger('collective.documentfusion.conversion')


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

    execute_job(__convert_document,
                obj, named_file, target_extension, fusion_data,
                conversion_name=conversion_name
                )


def convert_file(tmp_source_file_path, tmp_converted_file_path, target_ext,
                 fusion_data=None):
    """Uses py3o to convert a file into an other format
    filling properties, bookmarks and fields with data
    using libreoffice service
    """
    settings = getUtility(IRegistry).forInterface(ISettings)
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
        "http://%s:%s/form" % (settings.fusion_service_host, settings.fusion_service_port),
        data=fields,
        files=files,
        timeout=10.0,
    )
    if req.status_code != 400:
        chunk_size = 1024
        with open(tmp_converted_file_path, 'wb') as fd:
            for chunk in req.iter_content(chunk_size):
                fd.write(chunk)
    else:
        raise Py3oException("py3o.fusion server error: %s", req.text)

    assert os.path.exists(tmp_converted_file_path)


def get_converted_file(named_file, target_ext, fusion_data):
    """Get a converted file in a blob file
    from source named file, with target extension and fusion data as a dict.
    """
    tmp_source_file_path = store_namedfile_in_fs_temp(named_file)

    suffix = '--%s.%s' % (filename_split(named_file.filename)[0], target_ext)
    tmp_converted_file_path = tempfile.mktemp(suffix=suffix)

    try:
        convert_file(
            tmp_source_file_path,
            tmp_converted_file_path,
            target_ext,
            fusion_data
        )
        return get_blob_from_fs_file(tmp_converted_file_path)
    finally:
        remove_if_exists(tmp_source_file_path)
        remove_if_exists(tmp_converted_file_path)
