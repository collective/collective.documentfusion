# -*- encoding: utf-8 -*-
from copy import deepcopy
try:
    import json
except ImportError:
    import simplejson as json

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from collective.documentfusion import _
from collective.documentfusion.api import refresh_conversion
from collective.documentfusion.interfaces import IFusionStorage
from collective.documentfusion.interfaces import (
    TASK_IN_PROGRESS, TASK_FAILED, TASK_SUCCEEDED)
from plone import api
from plone.app.layout.viewlets.common import ViewletBase
from plone.namedfile.utils import stream_data, set_headers
from plone.protect import PostOnly
from zope.i18n import translate
from zope.i18nmessageid.message import MessageFactory

PMF = MessageFactory('plone')

NO_STATUS = 'no-status'

STATUS_MESSAGES = {
    NO_STATUS: {
        'id': NO_STATUS,
        'msg': _(u"No document generated here"),
        'status-label': PMF(u"Info"),
        'status-class': 'error',
        'downloadable': False,
        'allow-retry': True,
    },
    TASK_SUCCEEDED: {
        'id': TASK_SUCCEEDED,
        'msg': _(u"Get the generated file."),
        'status-label': PMF(u"Info"),
        'status-class': 'info',
        'downloadable': True,
        'allow-retry': True,
    },
    TASK_IN_PROGRESS: {
        'id': TASK_IN_PROGRESS,
        'msg': _(u"Processing document generation..."),
        'status-label': PMF(u"Info"),
        'status-class': 'info',
        'downloadable': False,
        'allow-retry': False,
    },
    TASK_FAILED: {
        'id': TASK_FAILED,
        'msg': _(u"Document generation failed, please retry or contact your administrator"),
        'status-label': PMF(u"Error"),
        'status-class': 'error',
        'downloadable': False,
        'allow-retry': True,
    }
}


class StatusViewletMixin(object):
    viewlet_template = ViewPageTemplateFile('viewlet.pt')
    conversion_name = NotImplemented
    make_pdf = None  # None, 1 or 0
    status = None  # status info for template
    icon_path = ''
    site_url = ''
    filename = ''

    def update(self):
        if self.conversion_name == NotImplemented:
            raise NotImplementedError('conversion_name is missing on %s at update time' % self)
        conversion_name = self.conversion_name
        storage = IFusionStorage(self.context)
        status = storage.get_status(conversion_name) or NO_STATUS
        self.status = deepcopy(STATUS_MESSAGES[status])
        self.site_url = api.portal.get().absolute_url()
        mimetype = storage.get_mimetype(conversion_name)
        file_obj = storage.get_file(conversion_name)
        if mimetype:
            self.icon_path = mimetype.icon_path
            self.filename = file_obj.filename

    def render_viewlet(self):
        return self.viewlet_template()


class DocumentFusionViewlet(StatusViewletMixin, ViewletBase):
    conversion_name = ''  # default one

    def index(self):
        return self.render_viewlet()


class StatusView(StatusViewletMixin, BrowserView):
    def render_status(self):
        request = self.request
        self.conversion_name = request.get('conversion', '')
        self.update()
        accept_header = request.getHeader('accept', '')
        if accept_header.lower() in ('application/json', 'text/json'):
            url = self.context.absolute_url()
            request.response.setHeader('Content-Type', 'application/json')
            status = {
                'conversion': self.conversion_name,
                'status': self.status['id'],
                'msg': translate(self.status['msg'], context=request),
                'statusLabel': translate(self.status['status-label'], context=request),
                'statusClass': self.status['status-class'],
                'icon': self.icon_path,
                'filename': self.filename,
            }
            if self.status['allow-retry']:
                status['refreshUrl'] = '{0}/@@refresh-documentfusion?conversion={1}'.format(
                    url, self.conversion_name)

            if self.status['downloadable']:
                status['downloadUrl'] = '{0}/@@download-documentfusion?conversion={1}'.format(
                    url, self.conversion_name)
            return json.dumps(status)
        else:
            return self.render_viewlet()


class DownloadView(BrowserView):
    def __call__(self):
        conversion_name = self.request.get('conversion', '')
        context, request = self.context, self.request
        storage = IFusionStorage(context)
        status = storage.get_status(conversion_name) or NO_STATUS
        named_file = storage.get_file(conversion_name)
        if status == TASK_SUCCEEDED:
            set_headers(named_file,
                        request.response, filename=named_file.filename)
            return stream_data(named_file)
        else:
            IStatusMessage(request).add(
                STATUS_MESSAGES[status]['msg'],
                type=STATUS_MESSAGES[status]['status-class'])

        redirect_to = request.get('redirect_fail', '')
        if not redirect_to:
            redirect_to = "%s/view" % context.absolute_url()
        return request.response.redirect(redirect_to)


class RefreshView(StatusViewletMixin, BrowserView):
    def enabled(self):
        return True

    def default_enabled(self):
        return False

    def refresh(self):
        context, request = self.context, self.request
        PostOnly(request)
        self.conversion_name = request.get('conversion', None)
        make_pdf = int(request['pdf']) if request.get('pdf', None) else None
        refresh_conversion(context,
                           conversion_name=self.conversion_name,
                           make_pdf=make_pdf)

        ajax_load = request.get('ajax_load', '')
        if ajax_load:
            self.update()
            return self.render_viewlet()

        redirect_to = request.get('redirect_to', '')
        if not redirect_to:
            redirect_to = "%s/view" % self.context.absolute_url()

        return request.response.redirect(redirect_to)
