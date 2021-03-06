from setuptools import setup, find_packages
import itertools

# Parse the version from the main __init__.py
with open('madmex/__init__.py') as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

# 
extra_reqs = {'docs': ['sphinx',
                       'sphinx-rtd-theme',
                       'sphinxcontrib-programoutput'],
              's3': ['boto3'],
              'xgboost': ['xgboost'],
              'multi': ['cloudpickle',
                        'distributed']}
extra_reqs['all'] = list(set(itertools.chain(*extra_reqs.values())))

setup(name='madmex',
      version=version,
      description=u"Scalable production of land cover and land cover change information",
      classifiers=[],
      keywords='Landsat, data cube, sentinel, rapidEye, Land cover',
      author=u"Amaury, Eric, Loic, Roberto",
      author_email='',
      url='https://github.com/CONABIO/antares3.git',
      license='GPLv3',
      packages=find_packages(),
      install_requires=[
          'python-dotenv',
          'Django',
          'xarray',
          'pyproj',
          'affine',
          'netCDF4',
          'jinja2',
          'requests',
          'datacube',
          'sklearn',
          'lightgbm',
          'scipy',
          'fiona',
          'shapely',
          'scikit-image',
          'dill',
          'pyyaml',
          'djangorestframework',
          'django-cors-headers'],
      entry_points={'console_scripts': [
          'antares = madmex.entry:main',
      ]},
      include_package_data=True,
      test_suite="tests",
      extras_require=extra_reqs)

