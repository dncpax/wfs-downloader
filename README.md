WFS Downloader
==============

Downloads GML files from a set of WFS service in a pseudo-paginated way using bounding boxes and combine them again to one file.
\n**This is a fork, heavily modified.** It uses GDAL/OGR to merge files instead of using xml. This allows to avoid duplicates by creating a geopackage with a unique index on a column defined in the .yml.
A few details:
 - merging is done in memory, using ogr/gdal, it's recommended to use 64bit python and gdal;
 - spatial index is disabled to make it faster, and created in a final step;
 - duplicates are now removed after merging, using sql and the unique field configured by the user - works well and is fast;
 - finally the in-memory geopackage is exported to a disk geopackage and a spatial index is created by sql;
Things look a lot faster in my tests:
- merge in disk: Data downloaded and processed in 7594.9134 seconds
- merge in memory: Data downloaded and processed in 2832.862000 seconds
- by removing duplicates and no spatial index: Data downloaded and processed in 2013.296000 seconds

Now because of in-memory merging it is recommended to use 64bit python and gdal.

Many other changes are minor. WFS 1.1.0 and 1.0.0 use numberOfFeatures instead of numberReturned/numberMatched. Also, in WFS2.0.0 when working with WGS84 (EPSG 4326) there's an inversion of axis that is now handled properly (I hope). Also, if a files exists it is not donwloaded again - this is to help in case the server starts erroring out so you can run the script multiple times and incrementally download all files. If you want to redownload a file you must delete it and rerun the script.
A few new configuration keys: version (for wfs), interval (to prevent service denial, imposes a pause between requests), uniqueid_field (to prevent duplicates).
Technically it merges files in memory, and in the end exports to file, always to a GeoPackage. If you need any other format you can convert by using GDAL/OGR or even easier by using QGIS.

Install
-------

You need to install GDAL binaries on your system first.
```
pip install wfs-downloader
```

Usage
-----

Create a `config.yml` specifying your setup like this:

```yml
url: http://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/s_wfs_baumbestand_an
layer: fis:s_wfs_baumbestand_an
version: 2.0.0

bbox:
  west:   370000.0
  south: 5800000.0
  east:   415000.0
  north: 5837000.0

size: 10000
interval: 5
outputfile: /<fullpath>/strassenbaeume.xml
uniqueid_field: gml_id
projection: EPSG:25833
tmpdir: /tmp
```

where:

* `url` is the url of the WFS Service,
* `layer` is the name of the Layer,
* `version` is the version of WFS to request,
* `bbox` is the bounding box for th objects you want to retrieve,
* `size` is the extend of a single request (or page),
* `interval' is the delay in second between requests to avoid errors from server like closed connection,
* `outputfile` is the name of the resulting GML file,
* `uniqueid_field` is the attribute that is unique identifier so we can prevent duplicates from being merged (important for polygon and line layers),
* `projection` is the used projection, and
* `tmpfile` is the path to the directory to store temporary files for each request.

Then run the script with the `config.yml` as argument:

```
wfs-downloader config.yml
```

Help
----

```
$ wfs-downloader --help
usage: Downloads GML files from a set of WFS service in a pseudo-paginated way using bounding boxes and combine them again to one file. The WFS services are specified in settings.py.

positional arguments:
  config         config file

optional arguments:
  -h, --help     show this help message and exit
  --no-download  skip the download
  --no-combine   skip the combine
```
