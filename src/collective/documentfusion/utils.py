import os
import tempfile

from plone.app.blob.utils import guessMimetype
from plone.namedfile.file import NamedBlobFile


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
