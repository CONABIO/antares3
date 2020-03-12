'''
Created on Dec 12, 2017

@author: agutierrez
'''

from django.contrib.gis.db import models
from django.contrib.gis.utils.layermapping import LayerMapping
from django.contrib.postgres.fields import JSONField


class Country(models.Model):
    '''This table stores the geometries for the countries.
    '''
    name = models.CharField(max_length=100, unique=True)
    the_geom = models.GeometryField()
    added = models.DateTimeField(auto_now_add=True)

class Region(models.Model):
    '''This model represents a region that can be related to a Country.
    '''
    name = models.CharField(max_length=100, unique=True)
    the_geom = models.GeometryField()
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='country', default=None)
    added = models.DateTimeField(auto_now_add=True)

class Footprint(models.Model):
    '''This model represents a footprint.
    '''
    name = models.CharField(max_length=50, unique=True)
    the_geom = models.GeometryField()
    sensor = models.CharField(max_length=50, default='')
    added = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    '''This model holds the information of usgs orders.
    '''
    user = models.CharField(max_length=50, default=None)
    order_id = models.CharField(max_length=100, unique=True)
    downloaded = models.BooleanField()
    added = models.DateTimeField(auto_now_add=True)

class Model(models.Model):
    '''A database entry that handles the models that we train.
    '''
    name = models.CharField(max_length=100, unique=True)
    path = models.CharField(max_length=300, unique=True)
    training_set = models.CharField(max_length=100)
    recipe = models.CharField(max_length=100, default=None)
    added = models.DateTimeField(auto_now_add=True)

class Tag(models.Model):
    '''To keep a deeper control over the tags that we can handle.
    '''
    scheme = models.CharField(max_length=50, default=None)
    value = models.CharField(max_length=150, default='')
    numeric_code = models.IntegerField(default=-1)
    color = models.CharField(max_length=7, default='')


class TrainObject(models.Model):
    '''This table holds objects that will be used for training. They must be related to
    regions and each object should have an assigned tag which is the ground truth for
    it.
    '''
    the_geom = models.GeometryField()
    added = models.DateTimeField(auto_now_add=True)
    training_tags = models.ManyToManyField(Tag,
                                           through='TrainClassification',
                                           through_fields=('train_object', 'interpret_tag'))
    filename = models.CharField(max_length=200, default='')
    creation_year = models.CharField(max_length=20, default='2015')

class SegmentationInformation(models.Model):
    '''This table will store information for a given segmentation object so it does not
    repeat for each polygon in the segmentation.
    '''
    algorithm = models.CharField(max_length=200, default='')
    datasource = models.CharField(max_length=200, default='')
    parameters = models.CharField(max_length=200, default='')
    datasource_year = models.CharField(max_length=20, default='2015')
    name = models.CharField(max_length=200, default='')

class PredictObject(models.Model):
    '''This table holds objects that will be used for training. They must be related to
    regions and each object should have an assigned tag which is the ground truth for
    it.
    '''
    path = models.CharField(max_length=400, unique=True)
    the_geom = models.GeometryField()
    added = models.DateTimeField(auto_now_add=True)
    segmentation_information = models.ForeignKey(SegmentationInformation, on_delete=models.CASCADE, default=-1)

class TrainClassification(models.Model):
    '''This tables relates the train objects with a tag, we add information about the
    dataset from which the object was taken.
    '''
    predict_tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='classification_predict', default=None)
    interpret_tag = models.ForeignKey(Tag, related_name='interpret_tag', on_delete=models.CASCADE)
    train_object = models.ForeignKey(TrainObject, related_name='train_object', on_delete=models.CASCADE)
    training_set = models.CharField(max_length=100, default='')

class Users(models.Model):
    '''Table that holds information regarding users that will label polygons using
    app.
    Will change to hold more info.
    '''
    first_name = models.CharField(max_length=30, default=None)
    last_name = models.CharField(max_length=30, default=None)
    email = models.CharField(unique=True, max_length=100, default=None)
    password = models.CharField(unique=True, max_length=100, default=None)

class Institutions(models.Model):
    '''Table that holds information regarding institutions where users will label
    polygons using app.
    '''
    name = models.CharField(unique=True, max_length=100, default=None)
class CatalogTrainingSetForApp(models.Model):
    '''Table that holds information regarding training sets that users of app will
    select from
    '''
    name = models.CharField(unique=True, max_length=100, default=None)
    scheme = models.CharField(max_length=50, default=None)
class TrainingSetAndODCTilesForApp(models.Model):
    '''Table that relates training sets in TrainClassificationLabeledByApp table
    with tiles of Open Data Cube. Therefore App just visualize a dc tile instead
    all objects from a region.
    '''
    training_set = models.ForeignKey(CatalogTrainingSetForApp, on_delete=models.CASCADE)
    odc_tile = models.CharField(max_length=10, default='')
    the_geom = models.GeometryField(null=True, blank=True)

class TrainClassificationLabeledByApp(models.Model):
    ''' Table created with the purpose of holding values created via App.
    Is similar to the one of TrainClassification
    For ForeignKey blank or null check: https://stackoverflow.com/questions/16589069/foreignkey-does-not-allow-null-values
    and: https://code.djangoproject.com/ticket/12708
    '''
    interpret_tag = models.ForeignKey(Tag, related_name='interpret_tag_app', on_delete=models.CASCADE, default=-1, blank=True, null=True)
    train_object = models.ForeignKey(TrainObject, related_name='train_object_app', on_delete=models.CASCADE)
    training_set = models.ForeignKey(CatalogTrainingSetForApp, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, default=-1,blank=True,null=True)
    institution = models.ForeignKey(Institutions, on_delete=models.CASCADE, default=-1,blank=True,null=True)
    automatic_label_tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    interpreted = models.BooleanField(default=False)
    odc_tile = models.ForeignKey(TrainingSetAndODCTilesForApp, on_delete=models.CASCADE, default=-1)

class ChangeInformation(models.Model):
    """Gathers information about change objects
    """
    year_pre = models.IntegerField(default=-1)
    year_post = models.IntegerField(default=-1)
    algorithm = models.CharField(max_length=100, default='')
    name = models.CharField(max_length=100, default='')

class ChangeObject(models.Model):
    """Table to store change geometries generated by the lcc.bitemporal change interface
    """
    the_geom = models.GeometryField()
    meta = models.ForeignKey(ChangeInformation, on_delete=models.CASCADE)

class ChangeClassification(models.Model):
    """Table to store pre and post land cover change information, relates to ChangeObject
    """
    pre_name = models.CharField(max_length=100, default='')
    post_name = models.CharField(max_length=100, default='')
    change_object = models.ForeignKey(ChangeObject, on_delete=models.CASCADE)
    pre_tag = models.ForeignKey(Tag, related_name='pre_tag', on_delete=models.CASCADE)
    post_tag = models.ForeignKey(Tag, related_name='post_tag', on_delete=models.CASCADE)

class ValidObject(models.Model):
    """The geometries of the validation datasets
    """
    the_geom = models.GeometryField()
    added = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=200, default='')
    validation_tags = models.ManyToManyField(Tag, through='ValidClassification')

class ValidClassification(models.Model):
    """Relates Validation objects to Tags
    """
    valid_tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    valid_object = models.ForeignKey(ValidObject, on_delete=models.CASCADE)
    valid_set = models.CharField(max_length=100, default='')
    interpretation_year = models.IntegerField(default=-1)


class ValidationResults(models.Model):
    """Log validation results
    """
    classification = models.CharField(max_length=100, default='')
    validation = models.CharField(max_length=100, default='')
    region = models.CharField(max_length=100, default='', null=True)
    scheme = models.CharField(max_length=100, default='')
    n_val = models.IntegerField(default=-1)
    n_pred = models.IntegerField(default=-1)
    overall_acc = models.FloatField(default=1.0)
    report = JSONField()
    comment = models.CharField(max_length=500, default='', null=True)
    added = models.DateTimeField(auto_now_add=True)

class PredictClassification(models.Model):
    '''This table relates predict object and a tag as a many to many table. We created an
    specific table for this to add information about the model.
    '''
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    predict_object = models.ForeignKey(PredictObject, on_delete=models.CASCADE)
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='model', default=None)
    name = models.CharField(max_length=200, default='')
    confidence = models.FloatField(default=-1.0)
    features_id = models.IntegerField(default=-1)

class Scene(models.Model):
    '''This table represents a satellite scene and information to build a catalalog.
    '''
    footprint = models.ForeignKey(Footprint, on_delete=models.CASCADE)
    scene_id = models.CharField(max_length=50,default=None, unique=True)
    landsat_product_id = models.CharField(max_length=50,default=None, unique=True)
    acquisition_date = models.DateTimeField(default=None)
    cloud_cover = models.FloatField(default=100.0)
    cloud_cover_land = models.FloatField(default=100.0)
    min_lat = models.FloatField(default=-1)
    min_lon = models.FloatField(default=-1)
    max_lat = models.FloatField(default=-1)
    max_lon = models.FloatField(default=-1)

def ingest_countries_from_shape(path, mapping):
    '''Ingestion function for countries to database.

    This function should be executed only once when the system is configured:

    Args:
        path (str): The path to the shape file.

    '''
    layer_mapping = LayerMapping(
        Country, path, mapping,
        transform=False, encoding='UTF-8 ',
    )
    layer_mapping.save()

def ingest_states_from_shape(path, mapping):
    '''Ingestion function for countries to database.

    This function should be executed only once when the system is configured:

    Args:
        path (str): The path to the shape file.

    '''
    layer_mapping = LayerMapping(
        Region, path, mapping,
        transform=False, encoding='UTF-8 ',
    )
    layer_mapping.save()
