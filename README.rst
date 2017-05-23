=========================
collective.documentfusion
=========================

Adds behaviours to make a merge between the variables, properties and bookmarks
of a file field with the fields of a dexterity content,
and publish the generated version of the document in its original format or in pdf format.

You can also make a merge between a field and several dexterity contents,
then it will generate a pdf with a version of the file successively merged with
each of those documents.
This is not dedicated to merge hundreds of documents, but fits well with few or dozens.

You can also use this product to simply provide pdf conversion of a file.


How to install fusion infrastructure
====================================

You have to get libreoffice installed on the system and run headless

    soffice --headless --accept="socket,host=127.0.0.1,port=2002;urp;" --nofirststartwizard


In your buildout, add parts that installs py3o: ::

    parts += py3o

    [py3o]
    recipe = zc.recipe.egg
    eggs =
        py3o.fusion
        py3o.renderserver


Then the services have to be started with accurate parameters, for instance: ::

    bin/start-py3o-fusion -s localhost -p 2003 -r 8888
    bin/start-py3o-renderserver -j /usr/lib/jvm/java-8-openjdk-amd64/jre/lib/amd64/server/libjvm.so -d juno -u /usr/share -o /usr/share/libreoffice -l 8888 -p 2002


Read the documentation of those services.


You can also use docker images. This is quite easier since you have docker infrastructure.
Your docker-compose will look like this (don't forget to set the image tags):

    py3ofusion:
        image: xcgd/py3o.fusion
        ports:
            - "127.0.0.1:8765:8765"
        links:
            - "py3orenderserver"

    py3orenderserver:
        image: xcgd/py3oserver-docker
        links:
            - "oooserver"
        volumes_from:
            - "oooserver"

    oooserver:
        image: xcgd/libreoffice


How to setup collective.documentfusion
======================================

Install the product on your plone site.

The following Plone registry fields allow you to configure the product behaviour:

- `auto_refresh_enabled` to allow / disallow automatic regeneration of conversion at each modification on documents (default `True`),
- `fusion_service_port` to tell Plone the port of the py3o.fusion service (default `8765`),
- `fusion_service_host` to tell the host where it is served (default `localhost`),
- `fusion_timeout` to set the maximum time we will wait for py3o.fusion service response (default `10`),
- `disable_async` to force conversion not to use async (default `False`).


How to use collective.documentfusion
====================================

You have to create a content type for your data. The field names have to be the same
than properties and variables you want to fill in your dexterity content type,
prefixed by **py3o.document.**. Read the
`py3o.template documentation <http://py3otemplate.readthedocs.io/en/latest/>`_

Many usecases are implemented.

Simple file to convert to pdf
-----------------------------

If you only select "collective.documentfusion: PDF Generation" behavior,
a pdf version of the first file field of your content will be published.

Simple content type with model file and data
--------------------------------------------

You can create a content type with a file field and the data field.
You just have to activate "collective.documentfusion: Document fusion" behavior
on the type. Each time you edit the content, a fused version of the content
will be generated each time you edit the document or you click 'refresh' action.

If you also select "collective.documentfusion: PDF Generation" behavior,
the generated file will be in pdf format.

Model file and data object
--------------------------

You can have the model and the data separated. Then you have two choices :

- The dexterity content with the data implements the behavior,
  it is related to the object with the model file.
- The dexterity file object implements the behavior, it is related to the content
  where the data is stored, using "Related items" behavior
  (there you also have to implement "collective.documentfusion: Merged document fusion" behavior)

Model file and several data objects
-----------------------------------

The file model is in a dexterity type that implements "Related items".
If you have selected the collective.documentfusion: Merged document fusion,
you can select several data objects. You'll get a pdf with one document per source.
Be careful, this product is not dedicated to generate hundreds of merged documents,
but to generate few ones.

Model file and collection
-------------------------

If you have selected a collection among the related items,
each result of the collection will be used as a source.


Extend
======

The way to get data from a content is an adapter of context and request that provides interface
**collective.documentfusion.interfaces.IFusionData**. This adapter returns a mapping of data to replace in file model.

An example of **IFusionData** adapter:

    class ProjectFusionData(object):
        adapts(IProject, IMyLayer)
        implements(IFusionData)

        def __init__(self, context, request):
            self.context = context
            self.request = request

        def __call__(self):
            context = self.context
            data = {'title': context.Title(), 'description': context.Description'}
            return data


The way to get images from a content is an adapter of context and request that provides interface
**collective.documentfusion.interfaces.IImageMapping**. The present package provides no default for this adapter.
This will replace the images named with a 'py3o.staticimage.' prefix like explained here:
`http://py3otemplate.readthedocs.io/en/latest/templating.html#insert-placeholder-images`
Note that if you need to include list of images for loops, you will use fusion data (cf `http://py3otemplate.readthedocs.io/en/latest/templating.html#insert-images-from-the-data-dictionary`).
Mapping format to return is {name of image without 'py3o.staticimage.' prefix: NamedFile with data of image}


The way to get the file field from a content is an adapter of context and request that provides interface
**collective.documentfusion.interfaces.IModelFileSource**. It returns a NamedFile containing the model file data.

An example of **IModelFileSource** adapter:

    MODEL_FILE = os.path.join(os.path.dirname(__file__), 'project-model.odt')
    EXTENDED_MODEL_FILE = os.path.join(os.path.dirname(__file__), 'extended-project-model.odt')

    class ProjectSourceFile(object):
        adapts(IProject, IMyLayer)
        implements(IModelFileSource)

        def __init__(self, context, request):
            self.context, self.request = context, request

        def __call__(self, recursive=True):
            if self.context.extended_project:
                model = EXTENDED_MODEL_FILE
            else:
                model = MODEL_FILE

            filename = normalizeString(unicode(self.context.Title()),
                                       context=self.context)
            return NamedFile(data=open(model).read(),
                             filename=unicode(filename) + u'.odt')


The way to get a list of data contents is an adapter of context and request that provides interface
**collective.documentfusion.interfaces.IMergeDataSources**.


If you need to consolidate data you get from sources during a merge fusion, you can write
a **collective.documentfusion.interfaces.IFusionDataReducer** adapter
where you will call IFusionData yourself and consolidate it with previous results.
The present package provides no default for this adapter.

Manual conversion
=================

If you don't want / need to use the behaviours,
(or if you want to add a conversion
on a content type that already have an automatic conversion),
you can create your own, you just have to implement **named adapters** for
**IFusionData**, **IModelFileSource** and (not mandatory) **IMergeDataSources**.

Then, you will be able to refresh the conversion using the view
`/@@documentfusion-refresh?conversion=my_conversion_name`.

and to get it using the view `@@getdocumentfusion/?conversion=my_conversion_name`

where my_conversion_name is the name you gave to the adapters.


Update document with custom conversion
--------------------------------------

You will need to subscribe on modified and manually execute refresh_conversion method

For instance (here we use grok for subscriber registration)

    @grok.subscribe(IMyProject, IObjectModifiedEvent)
    def update_report(project, event):
        refresh_conversion(project, conversion_name='report', make_pdf=False)


Async Integration
=================

It is highly recommended to install and configure plone.app.async
in combination with this package. Doing so will manage all generations
processes asynchronously so the user isn't delayed
so much when saving files.


Bypassing auto refresh
======================

Refresh is done at each document modification (on IObjectModified event).
You can globally disable this with auto_refresh_enabled registry setting.
You can globally disable it on the fly setting PREVENT_REFRESH_KEY value to True on request object.
