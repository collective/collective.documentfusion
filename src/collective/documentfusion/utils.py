import os
import tempfile

from collective.documentfusion import logger
from .interfaces import ISettings
from plone.app.blob.utils import guessMimetype
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError

try:
    from plone.app.async.interfaces import IAsyncService
    async_available = True
except ImportError:
    async_available = False


def filename_split(filename):
    return filename.rsplit('.', 1)


def remove_if_exists(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)


def store_namedfile_in_fs_temp(named_file):
    fs_path = tempfile.mktemp(suffix='--%s' % named_file.filename)
    file_obj = open(fs_path, 'w')
    file_obj.write(named_file.data)
    file_obj.close()
    assert os.path.exists(fs_path)
    return fs_path


def get_blob_from_fs_file(file_path):
    """get blob file from fs file. remove tmp prefix separated by --
    """
    file_obj = open(file_path)
    file_name = os.path.split(file_path)[-1].split('--')[-1]
    file_mimetype = guessMimetype(file_obj, filename=file_name)
    file_blob = NamedBlobFile(data=file_obj.read(),
                              contentType=file_mimetype,
                              filename=unicode(file_name))
    return file_blob


def execute_job(function, *args, **kwargs):
    """Execute job async
    @param function: function to execute
    args and kwargs:
    @param documentfusion_prevent_async: bool: if true, prevent async execution
    """
    if not async_available:
        prevent_async = True
    elif kwargs.pop('documentfusion_prevent_async', False):
        prevent_async = True
    else:
        settings = getUtility(IRegistry).forInterface(ISettings)
        prevent_async = settings.disable_async

    if not prevent_async:
        try:
            async = getUtility(IAsyncService)
            async.queueJob(function, *args, **kwargs)
            logger.info("Job queued: %s, %s, %s", function, args, kwargs)
            return
        except (ImportError, ComponentLookupError):
            pass

    function(*args, **kwargs)
