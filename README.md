WFS Downloader
==============

Downloads GML files from a set of WFS service in a pseudo-paginated way using bounding boxes and combine them again to one file.
This is a fork, heavily modified. It uses GDAL/OGR to merge files instead of using xml. This allows to avoid duplicates by creating a geopackage with a unique index on column gml_id or any unique attribute indicated in the .yml. This effectively causes an error when inserting the same gml_id. By ignoring these errors it continues to merge features that are not duplicates. 
Many other changes are minor. WFS 1.1.0 and 1.0.0 use numberOfFeatures instead of numberReturned/numberMatched. Also, in WFS2.0.0 when working with WGS84 (EPSG 4326) there's an inversion of axis that is now handled properly (I hope). Also, if a files exists it is not donwloaded again - this is to help in case the server starts erroring out so you can run the script multiple times and incrementally download all files. If you want to redownload a file you must delete it and rerun the script.
A few new configuration keys: version (for wfs), interval (to prevent service denial, imposes a pause between requests), uniqueid_field (to prevent duplicates).
Technically it merges files in memory, and in the end exports to file, always to a GeoPackage. If you need any other format you can convert by using GDAL/OGR or even easier by using QGIS.

Install
-------

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
* `uniqueid_field' is the attribute that is unique identifier so we can prevent duplicates from being merged (important for polygon and line layers),
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
