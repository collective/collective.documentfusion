import json
import logging
import os
import tempfile

import requests
from DateTime import DateTime
from collective.documentfusion.exceptions import Py3oException
from collective.documentfusion.interfaces import (
    ISettings, IFusionStorage, TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED)
from plone.registry.interfaces import IRegistry
from py3o.renderclient.client import RenderClient
from zope.component import getUtility
from .utils import (
    execute_job,
    filename_split,
    get_blob_from_fs_file,
    store_namedfile_in_fs_temp,
    remove_if_exists,
    get_fusion_data,
    get_image_mapping,
    get_model_file_source,
    get_target_extension)

logger = logging.getLogger('collective.documentfusion.conversion')


def __convert_document(obj, named_file, target_extension,
                       fusion_data=None, image_mapping=None, conversion_name=''):
    # section of convert_document process that should be run asyncronously
    storage = IFusionStorage(obj)
    try:
        converted_file = get_converted_file(
            named_file,
            target_extension,
            fusion_data=fusion_data,
            image_mapping=image_mapping
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
        
       @param obj: Object
            plone content from which we get
       @param target_extension: string
            The extension of output document. If not set,
            target_extension attribute of IModelSourceFile adapter will be used,
            else the extension of source file
       
       @param make_fusion: bool.
            If true, we will try to get fusion data and inject it into model using py3o.fusion
       
       @param conversion_name: string
            The name of the adapters to get source file, fusion data, image mapping
    """
    storage = IFusionStorage(obj)
    storage.set_file(None, conversion_name)
    storage.set_status(TASK_IN_PROGRESS, conversion_name)

    named_file = get_model_file_source(obj, obj.REQUEST, conversion_name)
    source_extension = filename_split(named_file.filename)[1]

    if not target_extension:
        target_extension = get_target_extension(obj, obj.REQUEST, conversion_name) or source_extension

    if make_fusion:
        fusion_data = get_fusion_data(obj, obj.REQUEST, conversion_name)
        image_mapping = get_image_mapping(obj, obj.REQUEST, conversion_name)
    else:
        fusion_data = None
        image_mapping = None

    execute_job(__convert_document,
                obj, named_file, target_extension,
                fusion_data=fusion_data, image_mapping=image_mapping,
                conversion_name=conversion_name
                )


def convert_fs_file(tmp_source_file_path, tmp_converted_file_path, target_ext,
                    fusion_data=None, image_mapping=None):
    """Uses py3o to convert a file stored on fs into an other
    filling properties, bookmarks and fields with data
    using libreoffice service
    """
    settings = getUtility(IRegistry).forInterface(ISettings)

    if not fusion_data and not image_mapping:
        # this is just a conversion, directly use converter
        client = RenderClient(settings.conversion_service_host, settings.conversion_service_port)
        client.render(tmp_source_file_path, tmp_converted_file_path, target_format=target_ext)
    else:
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
        }

        py3o_image_mapping = {}
        if image_mapping:
            for field, image_file in image_mapping.iteritems():
                py3o_image_mapping['staticimage.' + field] = 'staticimage.' + field
                fields['staticimage.' + field] = image_file.data

            fields['image_mapping'] = json.dumps(py3o_image_mapping)
        else:
            fields['image_mapping'] = "{}"

        req = requests.post(
            "http://%s:%s/form" % (settings.fusion_service_host, settings.fusion_service_port),
            data=fields,
            files=files,
            timeout=settings.fusion_timeout,
        )
        if req.status_code != 400:
            chunk_size = 1024
            with open(tmp_converted_file_path, 'wb') as fd:
                for chunk in req.iter_content(chunk_size):
                    fd.write(chunk)
        else:
            logger.error("Failed to convert file: %s with data: %s", files, fields)
            raise Py3oException("py3o.fusion server error: %s", req.text)

    assert os.path.exists(tmp_converted_file_path)


def get_converted_file(named_file, target_ext, fusion_data=None, image_mapping=None):
    """Get a converted file in a blob file
    from source named file, with target extension and fusion data and / or image mapping as a dict.
    @return NamedBlobFile
    """
    tmp_source_file_path = store_namedfile_in_fs_temp(named_file)

    suffix = '--%s.%s' % (filename_split(named_file.filename)[0], target_ext)
    tmp_converted_file_path = tempfile.mktemp(suffix=suffix)

    try:
        convert_fs_file(
            tmp_source_file_path,
            tmp_converted_file_path,
            target_ext,
            fusion_data=fusion_data,
            image_mapping=image_mapping
        )
        return get_blob_from_fs_file(tmp_converted_file_path)
    finally:
        remove_if_exists(tmp_source_file_path)
        remove_if_exists(tmp_converted_file_path)
