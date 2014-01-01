from zope.i18n import translate
from zope.annotation.interfaces import IAnnotations
from plone.app.layout.viewlets.common import ViewletBase
from plone.namedfile.utils import stream_data, set_headers
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from collective.documentfusion.interfaces import DATA_STORAGE_KEY,\
    STATUS_STORAGE_KEY
from collective.documentfusion.interfaces import TASK_SUCCEEDED
from collective.documentfusion import _


class DownloadLinkViewlet(ViewletBase):

    def render(self):
        context = self.context
        annotations = IAnnotations(context)
        status = annotations.get(STATUS_STORAGE_KEY, None)
        named_file = annotations.get(DATA_STORAGE_KEY, None)
        if status != TASK_SUCCEEDED:
            return u"" #@TODO: other statuses

        url = u"%s/getdocumentfusion" % context.absolute_url()
        title = translate(_(u"Get the generated file."), context=self.request)

        mtregistry = getToolByName(self.context, 'mimetypes_registry')
        file_name = named_file.filename
        mimetype = mtregistry.lookupExtension(file_name)
        icon_path = "%s/%s" % (self.portal_url, mimetype.icon)
        return u"""
        <div id="generated-pdf">
          <a href="%s" title="%s">
            <img src="%s" /> %s
          </a>
        </div>""" % (url, title, icon_path, file_name)


class DownloadView(BrowserView):

    def __call__(self):
        context = self.context
        annotations = IAnnotations(context)
        status = annotations.get(STATUS_STORAGE_KEY, None)
        named_file = annotations.get(DATA_STORAGE_KEY, None)
        if status != TASK_SUCCEEDED or not named_file:
            return u"" #@TODO: other statuses

        set_headers(named_file,
                    self.request.response, filename=named_file.filename)
        return stream_data(named_file)
