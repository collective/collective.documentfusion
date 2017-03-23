from collective.documentfusion.api import refresh_conversion

from collective.documentfusion.interfaces import (
    ISettings, PREVENT_REFRESH_KEY)
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.container.interfaces import IContainerModifiedEvent


def refresh(obj, event=None):
    # TODO: get all conversions
    if IContainerModifiedEvent.providedBy(event):
        return

    try:
        if obj.REQUEST.get(PREVENT_REFRESH_KEY, False):
            return
    except AttributeError:
        pass

    settings = getUtility(IRegistry).forInterface(ISettings)
    if settings.auto_refresh_enabled:
        refresh_conversion(obj)
