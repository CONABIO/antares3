"""antares33 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib.gis import admin
from django.urls import path, include
from rest_framework import routers

from madmex.rest import views


router = routers.DefaultRouter()
router.register(r'objects', views.ObjectViewSet)
router.register(r'predict', views.PredictViewSet)
router.register(r'footprints', views.FootprintViewSet)

urlpatterns = [
    path('datacube_landsat_tiles/', views.datacube_chunks, name='datacube_chunks'),
    path('datacube/', views.datacube_landsat_tiles, name='datacube_landsat_tiles'),
    path('training_objects/<int:z>/<int:x>/<int:y>/', views.training_objects, name='training_objects'),
    path('admin/', admin.site.urls),
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^$', views.map, name='map'),
]
