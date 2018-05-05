'''
Created on Dec 12, 2017

@author: agutierrez
'''

from django.contrib.gis.db import models
from django.contrib.gis.utils.layermapping import LayerMapping


class Country(models.Model):
    '''This table stores the geometries for the countries.
    '''
    name = models.CharField(max_length=100, unique=True)
    the_geom = models.MultiPolygonField()
    added = models.DateTimeField(auto_now_add=True)

class Region(models.Model):
    '''This model represents a region that can be related to a Country.
    '''
    name = models.CharField(max_length=100)
    the_geom = models.MultiPolygonField()
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='country', default=None)
    added = models.DateTimeField(auto_now_add=True)

class Footprint(models.Model):
    '''This model represents a footprint.
    '''
    name = models.CharField(max_length=50, unique=True)
    the_geom = models.PolygonField()
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
    value = models.CharField(max_length=150, default=None)
    numeric_code = models.IntegerField(default=-1)
    color = models.CharField(max_length=7, default='')


class TrainObject(models.Model):
    '''This table holds objects that will be used for training. They must be related to
    regions and each object should have an assigned tag which is the ground truth for
    it.
    '''
    models.GeometryField
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
    the_geom = models.GeometryField()
    added = models.DateTimeField(auto_now_add=True)
    prediction_tags = models.ManyToManyField(Tag, through='PredictClassification')
    segmentation_information = models.ForeignKey(SegmentationInformation, on_delete=models.CASCADE, default=-1)

class TrainClassification(models.Model):
    '''This tables relates the train objects with a tag, we add information about the
    dataset from which the object was taken.
    '''
    predict_tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='classification_predict', default=None)
    interpret_tag = models.ForeignKey(Tag, related_name='interpret_tag', on_delete=models.CASCADE)
    train_object = models.ForeignKey(TrainObject, related_name='train_object', on_delete=models.CASCADE)
    training_set = models.CharField(max_length=100, default='')

class PredictClassification(models.Model):
    '''This table relates predict object and a tag as a many to many table. We created an
    specific table for this to add information about the model.
    '''
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    predict_object = models.ForeignKey(PredictObject, on_delete=models.CASCADE)
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='model', default=None)
    name = models.CharField(max_length=200, default='')
    confidence = models.FloatField(default=-1.0)
    
class Scene(models.Model):
    '''This table represents a satellite scene and information to build a catalalog.
    '''
    footprint = models.ForeignKey(Footprint, on_delete=models.CASCADE)
    scene_id = models.CharField(max_length=50,default=None, unique=True)
    landsat_product_id = models.CharField(max_length=50,default=None, unique=True)
    acquisition_date = models.DateTimeField(default=None)
    day_night = models.CharField(max_length=50, default=None)
    image_quality = models.IntegerField(default=-1)
    cloud_cover = models.FloatField(default=-1.0)
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
