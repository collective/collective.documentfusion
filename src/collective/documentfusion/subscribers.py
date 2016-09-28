from collective.documentfusion.converter import refresh_conversion


def refresh(obj, event=None):
    # TODO: get all conversions
    refresh_conversion(obj)
