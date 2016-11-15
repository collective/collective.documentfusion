from collective.documentfusion.interfaces import (
    IFusionStorage, STATUS_STORAGE_KEY, DATA_STORAGE_KEY)
from zope.annotation.interfaces import IAnnotations, IAnnotatable
from zope.component import adapts
from zope.interface import implements


class FusionStorage(object):
    """Adapter to ease access to stored information
    """
    adapts(IAnnotatable)
    implements(IFusionStorage)

    def __init__(self, context):
        self.annotations = IAnnotations(context)

    def get_status(self, conversion_name=''):
        """Get conversion status: success, failure or pending.
        """
        if conversion_name:
            key = STATUS_STORAGE_KEY + '-' + conversion_name
        else:
            key = STATUS_STORAGE_KEY

        return self.annotations.get(key, None)

    def set_status(self, status, conversion_name=''):
        """Get conversion status: success, failure or pending.
        """
        if conversion_name:
            self.annotations[
                STATUS_STORAGE_KEY + '-' + conversion_name] = status
        else:
            self.annotations[STATUS_STORAGE_KEY] = status

    def get_file(self, conversion_name=''):
        """Get converted file.
        """
        if conversion_name:
            key = DATA_STORAGE_KEY + '-' + conversion_name
        else:
            key = DATA_STORAGE_KEY

        return self.annotations.get(key, None)

    def set_file(self, named_file, conversion_name=''):
        """Set converted file.
        """
        if conversion_name:
            self.annotations[
                DATA_STORAGE_KEY + '-' + conversion_name] = named_file
        else:
            self.annotations[DATA_STORAGE_KEY] = named_file
