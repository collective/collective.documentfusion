from zope.interface import Interface, implements
from zope.component import adapts

from plone.app.collection.interfaces import ICollection

from collective.documentfusion.interfaces import IMergeDataSources


class CollectionMergeDataSources(object):
    adapts(ICollection, Interface)
    implements(IMergeDataSources)

    def __init__(self, context, request):
        self.context = context

    def __call__(self):
        return [r.getObject() for r in self.context.results(batch=False)]
