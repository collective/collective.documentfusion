from collective.documentfusion.api import refresh_conversion

from collective.documentfusion.interfaces import (
    ISettings)
from plone.registry.interfaces import IRegistry
from zope.component import getUtility


def refresh(obj, event=None):
    # TODO: get all conversions
    settings = getUtility(IRegistry).forInterface(ISettings)
    if settings.auto_refresh_enabled:
        refresh_conversion(obj)
