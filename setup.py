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
                       'sphinxcontrib-programoutput']}
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
          'psycopg2'],
      scripts=['madmex.py'],
      test_suite="tests",
      extras_require=extra_reqs)

