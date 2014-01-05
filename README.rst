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


How to use it
=============

You have to create a content type for your data. The field names have to be the same
than properties, variables and bookmarks you want to fill in your dexterity content type.

Many usecases are implemented.

Simple file to convert to pdf
-----------------------------

If you only select "collective.documentfusion: PDF Generation" behavior,
a pdf version of the first file field of your content will be published.

Simple content type with model file and data
--------------------------------------------

You can create a content type with a file field and the data field.
You just have to activate "collective.documentfusion: Document fusion" behavior
on the type. Each time you edit the content, a merged version of the content
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
collective.documentfusion.interfaces.IFusionData

The way to get the file field from a content is an adapter of context and request that provides interface
collective.documentfusion.interfaces.ISourceFile

The way to get a list of data contents is an adapter of context and request that provides interface
collective.documentfusion.interfaces.IMergeDataSources