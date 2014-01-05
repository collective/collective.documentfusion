from zope.i18n import translate
from zope.i18nmessageid.message import MessageFactory
from zope.annotation.interfaces import IAnnotations

from plone.app.layout.viewlets.common import ViewletBase
from plone.namedfile.utils import stream_data, set_headers
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from collective.documentfusion.interfaces import DATA_STORAGE_KEY,\
    STATUS_STORAGE_KEY, TASK_IN_PROGRESS, TASK_FAILED
from collective.documentfusion.interfaces import TASK_SUCCEEDED
from collective.documentfusion import _
from collective.documentfusion.subscribers import refresh


PMF = MessageFactory('plone')

PORTAL_MESSAGE = u"""
            <dl class="portalMessage %(statusid)s">
                        <dt>%(status)s</dt>
                        <dd>%(msg)s</dd>
            </dl>
            """

class DownloadLinkViewlet(ViewletBase):

    def render(self):
        context = self.context
        annotations = IAnnotations(context)
        status = annotations.get(STATUS_STORAGE_KEY, None)
        named_file = annotations.get(DATA_STORAGE_KEY, None)
        if status == TASK_IN_PROGRESS:
            return PORTAL_MESSAGE % {'statusid': 'info',
                                     'status': PMF(u"Info"),
                                     'msg': _(u"Processing document generation, please refresh the page...")}
        elif status == TASK_FAILED:
            return PORTAL_MESSAGE % {'statusid': 'warning',
                                     'status': PMF(u"Error"),
                                     'msg': _(u"Document generation failed, please retry or contact your administrator")}

        url = u"%s/getdocumentfusion" % context.absolute_url()
        title = translate(_(u"Get the generated file."), context=self.request)

        mtregistry = getToolByName(self.context, 'mimetypes_registry')
        file_name = named_file.filename
        mimetype = mtregistry.lookupExtension(file_name)
        icon_path = "%s/%s" % (self.portal_url, mimetype.icon_path)
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


class RefreshView(BrowserView):

    def enabled(self):
        return True

    def default_enabled(self):
        return False

    def refresh(self):
        refresh(self.context, None)
        return self.request.response.redirect("%s/view" % self.context.absolute_url())