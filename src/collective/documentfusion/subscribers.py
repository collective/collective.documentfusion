from collective.documentfusion.api import refresh_conversion


def refresh(obj, event=None):
    # TODO: get all conversions
    refresh_conversion(obj)
