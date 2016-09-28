from zope.i18n import translate
from zope.i18nmessageid.message import MessageFactory
from zope.annotation.interfaces import IAnnotations

from plone.app.layout.viewlets.common import ViewletBase
from plone.namedfile.utils import stream_data, set_headers
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from collective.documentfusion.interfaces import DATA_STORAGE_KEY,\
    STATUS_STORAGE_KEY, TASK_IN_PROGRESS, TASK_FAILED
from collective.documentfusion.interfaces import TASK_SUCCEEDED
from collective.documentfusion import _
from collective.documentfusion.converter import refresh_conversion, apply_specific_conversion


PMF = MessageFactory('plone')

PORTAL_MESSAGE = u"""
            <dl class="portalMessage %(statusid)s">
                        <dt>%(status)s</dt>
                        <dd>%(msg)s</dd>
            </dl>
            """


class DownloadLinkViewlet(ViewletBase):

    def index(self):
        context = self.context
        annotations = IAnnotations(context)
        status = annotations.get(STATUS_STORAGE_KEY, None)
        named_file = annotations.get(DATA_STORAGE_KEY, None)
        if status == TASK_IN_PROGRESS:
            return PORTAL_MESSAGE % {'statusid': 'info',
                                     'status': PMF(u"Info"),
                                     'msg': translate(
                                         _(u"Processing document generation, "
                                           u"please refresh the page..."),
                                         context=self.request)}
        elif status == TASK_FAILED:
            return PORTAL_MESSAGE % {'statusid': 'warning',
                                     'status': PMF(u"Error"),
                                     'msg': translate(
                                         _(u"Document generation failed, "
                                           u"please retry "
                                           u"or contact your administrator"),
                                         context=self.request)}
        elif not status:
            return u""

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
        conversion = self.request.get('conversion', '')

        context = self.context
        # TODO: delegate storage
        annotations = IAnnotations(context)
        status = annotations.get(STATUS_STORAGE_KEY + conversion, None)
        named_file = annotations.get(DATA_STORAGE_KEY + conversion, None)
        if status == TASK_SUCCEEDED:
            set_headers(named_file,
                        self.request.response, filename=named_file.filename)
            return stream_data(named_file)

        if status == TASK_IN_PROGRESS:
            IStatusMessage(self.request).add(
                _(u"Document generation in progress, please retry later..."),
                type='warning')
        elif status == TASK_FAILED:
            IStatusMessage(self.request).add(
               _(u"Document generation failed, please retry document generation"
                 u" or contact your administrator..."),
               type='error')
        elif not status or not named_file:
            IStatusMessage(self.request).add(_(u"No document generated here"),
                                             type='error')

        self.request.response.redirect(self.context.absolute_url() + '/view')


class RefreshView(BrowserView):

    def enabled(self):
        return True

    def default_enabled(self):
        return False

    def refresh(self):
        conversion_name = self.request.get('conversion', '')
        pdf = self.request.get('pdf', None)
        if conversion_name or pdf:
            apply_specific_conversion(self.context,
                                      conversion_name=conversion_name,
                                      make_pdf=pdf)
        else:
            refresh_conversion(self.context)

        return self.request.response.redirect("%s/view" % self.context.absolute_url())
