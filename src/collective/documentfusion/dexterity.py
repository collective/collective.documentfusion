import datetime
from zope.interface import implements, Interface
from zope.component import getUtility, adapts, getMultiAdapter
from zope.component.interfaces import ComponentLookupError
from zope.schema import getFieldsInOrder
from zope.schema import getFields

from Products.CMFPlone.utils import base_hasattr
from plone import api
from plone.app.relationfield.behavior import IRelatedItems
from plone.dexterity.interfaces import IDexterityFTI, IDexterityContent
from plone.namedfile.interfaces import INamedField

from zope.component._api import queryMultiAdapter
from plone.behavior.interfaces import IBehavior
from plone.autoform.interfaces import IFormFieldProvider

from collective.documentfusion.interfaces import IModelFileSource, IFusionData, \
    IMergeDataSources
from collective.documentfusion.dexterityfields import IExportable


def get_fields(fti):
    schema = fti.lookupSchema()
    fields = getFields(schema)
    for behavior_id in fti.behaviors:
        schema = getUtility(IBehavior, behavior_id).interface
        if not IFormFieldProvider.providedBy(schema):
            continue
        fields.update(getFields(schema))

    return fields


class DexterityFusionData(object):
    adapts(IDexterityContent, Interface)
    implements(IFusionData)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):

        context = self.context
        data = {}
        data['document_id'] = context.id
        data['url'] = context.absolute_url()
        data['path'] = '/'.join(context.getPhysicalPath())
        data['uid'] = context.UID()
        if base_hasattr(context, 'title') and context.title:
            data['Title'] = context.title

        if base_hasattr(context, 'creators'):
            creator = context.creators[0]
            user = api.user.get(creator)
            if user:
                data['Author'] = user.getProperty('fullname', '') or creator
            else:
                data['Author'] = creator

        if base_hasattr(context, 'description') and context.description:
            description = context.description.replace('\n', ' ').strip()
            if description:
                data['Subject'] = data['Description'] = description

        if base_hasattr(context, 'subject') and context.subject:
            keywords = tuple([k.strip() for k in context.subject if k.strip()])
            data['Keywords'] = keywords

        fti = getUtility(IDexterityFTI, name=context.portal_type)
        fields = get_fields(fti)

        for name in fields:
            try:
                renderer = getMultiAdapter((fields[name], self.context, self.request),
                                     interface=IExportable,
                                     name=name)
            except ComponentLookupError:
                renderer = getMultiAdapter((fields[name], self.context, self.request),
                                     interface=IExportable)

            render = renderer.render(self.context)
            if type(render) is datetime.date:
                render = render.strftime("%Y-%m-%d")
            data[name] = render

        return data



class DexteritySourceFile(object):
    adapts(IDexterityContent, Interface)
    implements(IModelFileSource)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, recursive=True):
        # look for a content with name file field into content
        fti = getUtility(IDexterityFTI, name=self.context.portal_type)
        schema = fti.lookupSchema()
        for name, field in getFieldsInOrder(schema):
            if INamedField.providedBy(field):
                return getattr(self.context, name)

        # else, look for a source file field into related items
        if recursive and IRelatedItems.providedBy(self.context):
            related_items = [r.to_object for r in self.context.relatedItems]
            for related_item in related_items:

                source_file = getMultiAdapter((related_item, self.request),
                                              IModelFileSource
                                              )()
                if source_file:
                    return source_file
                else:
                    continue

        return None


class RelatedItemsMergeDataSources(object):
    """Get related items and data source got from direct related items"""
    adapts(IRelatedItems, Interface)
    implements(IMergeDataSources)

    def __init__(self, context, request):
        self.context = context

    def get_cascading_data_sources(self, obj):
        adapter = queryMultiAdapter((obj, self.context.REQUEST),
                                    interface=IMergeDataSources,
                                    default=None)
        if adapter and adapter.__class__ != RelatedItemsMergeDataSources:
            return adapter()
        else:
            return [obj]

    def __call__(self):
        sources = []
        for r in self.context.relatedItems:
            obj = r.to_object
            sources.extend(self.get_cascading_data_sources(obj))

        return sources
