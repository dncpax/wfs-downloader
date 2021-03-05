from __future__ import print_function

import argparse
import os
import yaml
import sys
import time
from osgeo import gdal
from osgeo import ogr

try:
    # py2
    from urllib import urlretrieve
    import urllib
    import time
except ImportError:
    # py3
    from urllib.request import urlretrieve
    import urllib.request

from lxml import etree


def main():

    if (sys.version_info.major >2):
      tic = time.perf_counter()
    else:
      tic = time.time()

    parser = argparse.ArgumentParser(usage='Downloads GML files from a set of WFS service in a pseudo-paginated way using bounding boxes and combine them again to one file. The WFS services are specified in settings.py.')
    parser.add_argument('config', help='config file')
    parser.add_argument('--no-download', help='skip the download', action='store_true')
    parser.add_argument('--no-combine', help='skip the combine', action='store_true')

    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.load(f.read())

    if not args.no_download:
        download_files(config)

    if not args.no_combine:
        combine_files(config)
        
    if (sys.version_info.major >2):
      toc = time.perf_counter()
    else:
      toc = time.time()
    print("Data downloaded and processed in %f seconds" % (toc-tic))


def download_files(config):

    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'wfs-downloader/0.1')]
        urllib.request.install_opener(opener)
    else:
        # Python 2 code in this block
        urllib.URLopener.version = "wfs-downloader/0.1"

    west_range = list(arange(config['bbox']['west'], config['bbox']['east'], config['size']))
    south_range = list(arange(config['bbox']['south'], config['bbox']['north'], config['size']))
    
    #switch axis if wgs84
    if(config['projection']=='EPSG:4326'):
        tmp_range = south_range
        south_range = west_range
        west_range = tmp_range

    for west in west_range:
        for south in south_range:

            url = '%(url)s?service=WFS&request=GetFeature&version=%(version)s&typeNames=%(layer)s&srsName=%(srid)s&BBOX=%(west)f,%(south)f,%(east)f,%(north)f' % {
                'url': config['url'],
                'version': config['version'],
                'layer': config['layer'],
                'srid': config['projection'],
                'west': west,
                'east': west + config['size'],
                'south': south,
                'north': south + config['size']
            }

            name, extension = os.path.splitext(os.path.basename(config['outputfile']))
            filename = os.path.join(config['tmpdir'], '%(name)s_%(west)s_%(south)s%(extension)s' % {
                'name': name,
                'west': west,
                'south': south,
                'extension': extension
            })
            #if filename already exists, pass
            if(os.path.exists(filename)):
              print ("File exists: %s. Skipping..." % filename)
              continue
              
            print('fetching %s' % filename)
            print('url: %s' % url)
            #we should manage errors of connection closed by the server with a cooldown timer and some retries
            try:
                urlretrieve(url, filename)
            except Exception as e:
                print ("Connection reset by server. Cooling down and retrying... You should try a smaller size and/or a bigger interval.")
                time.sleep(10)
                try:
                    urlretrieve(url, filename)
                except Exception as e1:
                    print ("Second failure... quiting downloading. Will merge existing files.")
                    os.remove(filename)
                    return
            
            #inspect file and delete if no elements found
            tree = etree.parse(filename)
            #attribute we want: numberReturned
            root = tree.getroot()
            if(config['version'] != '2.0.0'):
                numberOfFeatures = root.get('numberOfFeatures')
                print("Number of Features: %s" % numberOfFeatures)
            else:
                numberReturned = root.get('numberReturned')
                print("Features returned: %s" % numberReturned)
                numberMatched = root.get('numberMatched')
                print("Features matched: %s" % numberMatched)
#            if (numFeatures=="0"):
#                print ("0 features: deleting file")
#                os.remove(filename)
            #if there's an interval configured apply it now
            if (config['interval']>0): 
                print ("Interval of %ss defined. Waiting..." % config['interval'])
                time.sleep(config['interval'])


def combine_files(config):
    # read the first xml file
    name, extension = os.path.splitext(os.path.basename(config['outputfile']))
    print ("name=%s ;;;;;;;;; extension=%s" %(name, extension))
    #when wgs84 switch axis
    if(config['projection']=='EPSG:4326'):
        first_filename = os.path.join(config['tmpdir'], '%(name)s_%(west)s_%(south)s%(extension)s' % {
          'name': name,
          'west': config['bbox']['west'],
          'south': config['bbox']['south'],
          'extension': extension
        })
    else:
        first_filename = os.path.join(config['tmpdir'], '%(name)s_%(west)s_%(south)s%(extension)s' % {
            'name': name,
            'west': config['bbox']['south'],
            'south': config['bbox']['west'],
            'extension': extension
        })

    first_filename = os.path.join(config['tmpdir'], '%(name)s_%(west)s_%(south)s%(extension)s' % {
      'name': name,
      'west': config['bbox']['south'],
      'south': config['bbox']['west'],
      'extension': extension
    })
    print("first filename = %s" % first_filename)

    first_xml = etree.parse(first_filename)
    first_root = first_xml.getroot()
    nsmap = first_root.nsmap

    try:
        number_matched = int(first_root.get('numberMatched'))
    except (ValueError, TypeError):
        number_matched = False
    print ("number_matched=%i" % number_matched)

    try:
        number_returned = int(first_root.get('numberReturned'))
    except (ValueError, TypeError):
        number_returned = False
    print ("number_returned=%i" % number_returned)
    
    #for wfs 1.1.0 or 1.0.0
    try:
        number_offeatures = int(first_root.get('numberOfFeatures'))
    except (ValueError, TypeError):
        number_offeatures = False
    print ("number_offeatures=%i" % number_offeatures)
    
    #write with ogr: write to memory, merge, and finally export to file
    gdaloutputfile = config['outputfile'].replace(extension,".gpkg")
    print("Exporting: %s" % gdaloutputfile)
    gdal.UseExceptions()
    gdalDriverName = 'GPKG'
    
    #teste de remocao de duplicados
    #geopkg = gdal.OpenEx(gdaloutputfile, gdal.OF_UPDATE)
    #geopkg.ExecuteSQL("pragma wal_checkpoint(TRUNCATE)")
    #quit()
    #layer = geopkg.GetLayer(0)
    #nome = geopkg.GetLayer(0).GetName()
    #layer.ResetReading();
    #print("delete from %s where rowid not in (select min(rowid) from %s group by %s);" % (nome, nome, config['uniqueid_field']))
    #geopkg.ExecuteSQL("delete from %s where rowid not in (select min(rowid) from %s group by %s);" % (nome, nome, config['uniqueid_field']))
    #del geopkg
    #quit()
    
    srcDS = gdal.OpenEx(first_filename)
    srcLayer = srcDS.GetLayer(0)
    #spatialRef = srcDS.GetSpatialRef().exportToWkt()
    #options to create and append data - skipfailures if important to continue even when a duplicate fails to be added bc the unique index prevents it
    ogrOptions = gdal.VectorTranslateOptions(options=[
        '-f', gdalDriverName,
        '-t_srs', 'EPSG:4326',
        '-update',
        '-append',
        '-skipfailures',
        '-lco', 'SPATIAL_INDEX=NO'
    ])
    driver = ogr.GetDriverByName(gdalDriverName)
    if os.path.exists(gdaloutputfile):
         print("Deleting existing file: %s" % gdaloutputfile)
         deleted = driver.DeleteDataSource(gdaloutputfile)
         if(deleted != 0):
            print("impossible to delete... quiting.")
            quit()
         
    #ds = gdal.VectorTranslate(gdaloutputfile, srcDS=first_filename, options=ogrOptions)
    #gdalName=ds.GetLayer(0).GetName()
    outmemfile = os.path.join('/vsimem', os.path.basename(gdaloutputfile))
    print ('outmemfile=%s' % outmemfile)
    ds = gdal.VectorTranslate(outmemfile, srcDS=first_filename, options=ogrOptions)
    
    #try to optimize geopackage performance
    #memLayer = ds.GetLayer(0)
    #memLayerName = memLayer.GetName()
    #ds.ExecuteSQL('CREATE UNIQUE INDEX IF NOT EXISTS gmlid_idx ON "%s" (%s);' % (outmemfile, config['uniqueid_field']))
    
    #add a unique index to avoid duplicates if it is configured
    if (config['uniqueid_field'] != 'None'):
      #ds.ExecuteSQL('CREATE UNIQUE INDEX IF NOT EXISTS gmlid_idx ON "%s" (%s);' % (memLayerName, config['uniqueid_field']))
      pass
    #Dereference and close dataset, then reopen.
    del ds
    
    for filename in os.listdir(config['tmpdir']):
        print("filename=%s" % filename)
        if filename.startswith(name):
            abs_filename = os.path.join(config['tmpdir'], filename)
            if abs_filename != first_filename:
                print('merging', abs_filename)

                xml = etree.parse(abs_filename)
                root = xml.getroot()

                if number_matched is not False:
                    number_matched += int(root.get('numberMatched'))
                    print("elements in file=%s" % root.get('numberMatched'))
                    print ("elements total=%i" % number_matched)

                if number_returned is not False:
                    number_returned += int(root.get('numberReturned'))
                    print("elements in file=%s" % root.get('numberMatched'))
                    print ("elements total=%i" % number_returned)
                    
                if number_offeatures is not False:
                    number_offeatures += int(root.get('numberOfFeatures'))
                    print("elements in file=%s" % root.get('numberOfFeatures'))
                    print ("elements total=%i" % number_offeatures)

                #avoid errors in merging if 0 elements
                if(number_matched==0 and number_returned==0 and number_offeatures==0):
                    print("Empty file... skipping.")
                    continue
                    
                #for node in xml.xpath('.//wfs:member', namespaces=nsmap):
                #    first_root.append(node)
                #ds = gdal.VectorTranslate(gdaloutputfile, srcDS=abs_filename, options=ogrOptions)
                #Dereference and close dataset, then reopen.
                #del ds
                ds = gdal.VectorTranslate(outmemfile, srcDS=abs_filename, options=ogrOptions)
                #remove duplicates
                #if (config['uniqueid_field'] != 'None'):
                #  ds.ExecuteSQL('CREATE UNIQUE INDEX IF NOT EXISTS gmlid_idx ON "%s" (%s);' % (memLayerName, config['uniqueid_field']))

                #Dereference and close dataset, then reopen.
                del ds

                #memOptions = [
                #    '-f', 'memData',
                #    '-t_srs', 'EPSG:4326',
                #    '-update',
                #    '-append',
                #    '-skipfailures'
                #]
                #ds = gdal.VectorTranslate(layer_mem, srcDS=abs_filename, options=memOptions)

    # manipulate numberMatched numberReturned
    if number_matched is not False:
        first_root.set('numberMatched', str(number_matched))

    if number_returned is not False:
        first_root.set('numberReturned', str(number_returned))
        
    if number_offeatures is not False:
        first_root.set('numberOfFeatures', str(number_offeatures))

    #manipulate the extend / bounding box
    #avoid errors in merging if 0 elements
    if(number_matched>0 or number_returned>0 or number_offeatures>0):
        pass
        #in my case these attributes don't exist
        #first_root.xpath('.//wfs:boundedBy/gml:Envelope/gml:lowerCorner', namespaces=nsmap)[0].text = '%s %s' % (config['bbox']['west'], config['bbox']['east'])
        #first_root.xpath('.//wfs:boundedBy/gml:Envelope/gml:upperCorner', namespaces=nsmap)[0].text = '%s %s' % (config['bbox']['south'], config['bbox']['north'])
    else:
        print("No results - merged file not written.")

    #print("a escrever etree para %s" % config['outputfile'])
    #print("etree first xml=%s" % etree.tostring(first_xml))
    #with open(config['outputfile'], 'wb') as f:
    #    f.write(etree.tostring(first_xml))
    #    f.close()
    
    #remove duplicates before exporting to disk
    #teste de remocao de duplicados
    memgeopkg = gdal.OpenEx(outmemfile, gdal.OF_UPDATE)
    #geopkg.ExecuteSQL("pragma wal_checkpoint(TRUNCATE)")
    #quit()
    if (config['uniqueid_field'] is not None):
      layer = memgeopkg.GetLayer(0)
      nome = memgeopkg.GetLayer(0).GetName()
      print("Deleting duplicates based on unique fields: %s" % config['uniqueid_field'])
      memgeopkg.ExecuteSQL('delete from "%s" where rowid not in (select min(rowid) from "%s" group by "%s");' % (nome, nome, config['uniqueid_field']))
      del memgeopkg
    
    #write from memory to disk
    #print("Exporting from memory to disk: %s." % gdaloutputfile)
    #we can maybe optimize write performance using PRAGMA directives from SQLite
    #geopkg = driver.CreateDataSource(gdaloutputfile)
    #geopkg.ExecuteSQL("PRAGMA main.page_size = 4096;");
    #geopkg.ExecuteSQL("PRAGMA main.cache_size=10000;");
    #geopkg.ExecuteSQL("PRAGMA main.locking_mode=EXCLUSIVE;");
    #geopkg.ExecuteSQL("PRAGMA main.synchronous=NORMAL;");
    #geopkg.ExecuteSQL("PRAGMA main.journal_mode=WAL;");
    #geopkg.ExecuteSQL("PRAGMA main.cache_size=5000;");
    
    print("Configuring gdal to optimize GeoPackage write performance...")
    gdal.SetConfigOption('OGR_SQLITE_PRAGMA', 'main.page_size=4096,main.cache_size=10000,main.cache_size=5000')
    print("Writing to disk... %s" % gdaloutputfile)
    ds = gdal.VectorTranslate(gdaloutputfile, srcDS=outmemfile, options=ogrOptions)
    print("Creating spatial index...")
    layer = ds.GetLayer(0)
    layerName = layer.GetName()
    print ("layerName: %s" % layerName)
    geomFieldName = layer.GetLayerDefn().GetGeomFieldDefn(0).GetName()
    print("geom name: %s" % geomFieldName)
    ds.ExecuteSQL("SELECT CreateSpatialIndex('%s','%s')" % (layerName, geomFieldName));
    del ds

def arange(start, stop, step):
    current = start
    while current < stop:
        yield current
        current += step


if __name__ == "__main__":
    main()
