from zope.interface import implements, Interface
from zope.component import adapts


from collective.documentfusion.interfaces import IModelFileSource
from Products.Archetypes.interfaces.base import IBaseContent
from Products.Archetypes.interfaces.field import IFileField
from plone.app.blob.interfaces import IBlobField


class SourceFile(object):
    adapts(IBaseContent, Interface)
    implements(IModelFileSource)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, recursive=True):
        # look for a content with name file field into content
        field = self.context.getPrimaryField()
        for field in [self.context.getPrimaryField()] \
                + self.context.Schema().values():
            if IBlobField.providedBy(field) or IFileField.providedBy(field):
                return self.context.getField('file').get(self.context)
            #@TODO: should work with a basic IFileField
        else:
            return None