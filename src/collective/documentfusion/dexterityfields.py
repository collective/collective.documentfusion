# -*- encoding: utf-8 -*-

from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import base_hasattr
from plone.app.textfield.interfaces import IRichText
from plone.dexterity.interfaces import IDexterityContent
from plone.namedfile.interfaces import INamedField
from plone.schemaeditor.schema import IChoice
from z3c.form.interfaces import NO_VALUE
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import Interface
from zope.interface.declarations import implements
from zope.schema import getFieldsInOrder
from zope.schema.interfaces import IField, IDate, ICollection, \
    IVocabularyFactory, IBool


class IExportable(Interface):
    """Render a value from a field
    """

    def render(self, obj):
        """Gets the value to render in document from content
        """


class IFieldValueGetter(Interface):
    """Adapter to get a value from fieldname
    """

    def get(self, fieldname):
        """Get value from fieldname
        """


class DexterityValueGetter(object):
    adapts(IDexterityContent)
    implements(IFieldValueGetter)

    def __init__(self, context):
        self.context = context

    def get(self, field):
        return getattr(self.context, field.__name__, None)


class BaseFieldRenderer(object):
    implements(IExportable)

    def __init__(self, field, context, request):
        self.field = field
        self.context = context
        self.request = request

    def __repr__(self):
        return "<%s - %s>" % (self.__class__.__name__,
                              self.field.__name__)

    def get_value(self, obj):
        return IFieldValueGetter(obj).get(self.field)

    def render(self, obj):
        value = self.get_value(obj)
        if value == NO_VALUE:
            return None
        else:
            return value

    def render_collection_entry(self, obj, value):
        """Render a value element if the field is a sub field of a collection
        """
        return str(value or "")


class FieldRenderer(BaseFieldRenderer):
    adapts(IField, Interface, Interface)


class FileFieldRenderer(BaseFieldRenderer):
    adapts(INamedField, Interface, Interface)

    def render(self, obj):
        """Gets the value to render in excel file from content value
        """
        value = self.get_value(obj)
        return value and value.filename or ""


class BooleanFieldRenderer(BaseFieldRenderer):
    adapts(IBool, Interface, Interface)

    def render(self, obj):
        value = self.get_value(obj)
        return value and 1 or 0


class DateFieldRenderer(BaseFieldRenderer):
    adapts(IDate, Interface, Interface)

    def render(self, obj):
        return self.render_collection_entry(obj, self.get_value(obj))

    def render_collection_entry(self, obj, value):
        return value and value.strftime('%Y/%m/%d') or ""


class ChoiceFieldRenderer(BaseFieldRenderer):
    adapts(IChoice, Interface, Interface)

    def _get_vocabulary_value(self, obj, value):
        if not value:
            return value

        vocabulary = self.field.vocabulary
        if not vocabulary:
            vocabulary_name = self.field.vocabularyName
            if vocabulary_name:
                vocabulary = getUtility(IVocabularyFactory, name=vocabulary_name)(obj)

        if vocabulary:
            try:
                term = vocabulary.getTermByToken(value)
            except LookupError:
                term = None
        else:
            term = None

        if term:
            title = term.title
            if not title:
                return value
            else:
                return title
        else:
            return value

    def render(self, obj):
        value = self.get_value(obj)
        voc_value = self._get_vocabulary_value(obj, value)
        return voc_value

    def render_collection_entry(self, obj, value):
        voc_value = self._get_vocabulary_value(obj, value)
        return voc_value and translate(voc_value, context=self.request) or u""


class CollectionFieldRenderer(BaseFieldRenderer):
    adapts(ICollection, Interface, Interface)

    def render(self, obj):
        """Gets the value to render in excel file from content value
        """
        value = self.get_value(obj)
        sub_renderer = getMultiAdapter((self.field.value_type,
                                        self.context, self.request),
                                       interface=IExportable)
        return value and u"\n".join(["- " + sub_renderer.render_collection_entry(obj, v)
                                     for v in value]) or u""


class RichTextFieldRenderer(BaseFieldRenderer):
    adapts(IRichText, Interface, Interface)

    def render(self, obj):
        """Gets the value to render in excel file from content value
        """
        value = self.get_value(obj)
        if not value or value == NO_VALUE:
            return ""

        ptransforms = getToolByName(obj, 'portal_transforms')
        text = ptransforms.convert('text_to_html', value.output).getData()
        if len(text) > 50:
            return text[:47] + u"..."


try:
    from z3c.relationfield.interfaces import IRelation

    HAS_RELATIONFIELD = True


    class RelationFieldRenderer(BaseFieldRenderer):
        adapts(IRelation, Interface, Interface)

        def render(self, obj):
            value = self.get_value(obj)
            return self.render_collection_entry(obj, value)

        def render_collection_entry(self, obj, value):
            return base_hasattr(value, 'to_object') and value.to_object and value.to_object.Title() or u""

except ImportError:
    HAS_RELATIONFIELD = False

try:
    from collective.z3cform.datagridfield.interfaces import IRow

    HAS_DATAGRIDFIELD = True


    class DictRowFieldRenderer(BaseFieldRenderer):
        adapts(IRow, Interface, Interface)

        def render_collection_entry(self, obj, value):
            fields = getFieldsInOrder(self.field.schema)
            field_renderings = []
            for fieldname, field in fields:
                sub_renderer = getMultiAdapter((field,
                                                self.context, self.request),
                                               interface=IExportable)
                field_renderings.append(u"%s : %s" % (
                    sub_renderer.render_header(),
                    sub_renderer.render_collection_entry(obj,
                                                         value.get(fieldname))))

            return u" / ".join([r for r in field_renderings])

        def render(self, obj):
            value = self.get_value(obj)
            return self.render_collection_entry(obj, value)

except ImportError:
    HAS_DATAGRIDFIELD = False

try:
    from collective.contact.widget.interfaces import IContactChoice

    HAS_CONTACT_CORE = True


    class ContactChoiceFieldRenderer(BaseFieldRenderer):
        adapts(IContactChoice, Interface, Interface)

        def render(self, obj):
            value = self.get_value(obj)
            return self.render_collection_entry(obj, value)

        def render_collection_entry(self, obj, value):
            return value and value.to_object and value.to_object.get_full_title() or u""

except ImportError:
    HAS_CONTACT_CORE = False
