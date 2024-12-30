import os
import math
import numpy as np

import ee
import rasterio as rio

project = 'your-project'
ee.Initialize(project=project, opt_url='https://earthengine-highvolume.googleapis.com')

def naip(file):
    """
    
    Creates NAIP composite given the CHM GeoTiff produced by chm.R. The
    composite consists of the closest NAIP collection event two years before or
    after the CHM date.

    Args:
        file (str): file name of canopy height model, as produced by chm.R
    
    """

    file_info = os.path.splitext(file)[0].split('_')
    lidar_date = file_info[3]

    with rio.open(file) as src:
        profile = src.profile

    origin = [profile['transform'][2], profile['transform'][5]]

    years = 2
    start_date_ee = ee.Date(lidar_date)
    start_date_millis = start_date_ee.millis()
    
    geometry = ee.Geometry.Point(origin, ee.Projection(profile['crs'].to_string()))
    feature = ee.Feature(geometry, {'system:time_start': start_date_millis,
                                    'system:time_end': start_date_millis})
    
    naip = (ee.ImageCollection('USDA/NAIP/DOQQ')
      .filterBounds(geometry.buffer(200))
      .filterDate(start_date_ee.advance(-years, 'year'),
                  start_date_ee.advance(years, 'year'))
      .filter(ee.Filter.stringStartsWith('system:index', 'm_'))
    )
    
    years_millis = years * 365 * 24 * 60 * 60 * 1000
    
    time_filter = ee.Filter.Or(
        ee.Filter.maxDifference(
            difference=years_millis,
            leftField='system:time_start',
            rightField='system:time_end'
        ),
        ee.Filter.maxDifference(
            difference=years_millis,
            leftField='system:time_end',
            rightField='system:time_start'
        )
    )
    
    time_join = ee.Join.saveAll(
        matchesKey='naip',
        ordering='system:time_start',
        ascending=True,
        measureKey='time_distance'
    )
    
    feature_joined = time_join.apply(ee.FeatureCollection(feature), naip, time_filter)
    
    naip_millis = (ee.ImageCollection.fromImages(feature_joined.first().get('naip'))
      .sort('time_distance')
      .first()
      .get('system:time_start')
    )
    naip_date = ee.Date(naip_millis).format('YYYY-MM-dd')
    naip_range = ee.Date(naip_millis).getRange('year')
    
    
    def add_index(image):
      time_distance = ee.Number(image.get('time_distance'))
      index = ee.Number(1).divide(time_distance)
      index_band = ee.Image(index).rename(['index']).toFloat()
      return image.addBands(index_band)
    
    naip_proj = naip.first().projection()
    
    naip_mosaic = (ee.ImageCollection.fromImages(feature_joined.first().get('naip'))
      .filterDate(naip_range)
      .map(add_index)
      .qualityMosaic('index')
      .select(['R', 'G', 'B', 'N'])
      .setDefaultProjection(naip_proj)
    )
    
    mask = naip_mosaic.mask().reduce(ee.Reducer.min()).uint8().rename('mask')
    naip_mosaic = naip_mosaic.addBands(mask)

    naip_resolution = naip_mosaic.projection().nominalScale()

    try:
      naip_dict = ee.Dictionary({
          'start_date': naip_date,
          'resolution': naip_resolution
          }).getInfo()
    except ee.ee_exception.EEException:
        return file + ' naip error'

    resolution = naip_dict['resolution']
    height = math.ceil(profile['height'] / resolution)
    width = math.ceil(profile['width'] / resolution)
    
    new_profile = {}
    new_profile['transform'] = rio.transform.Affine(resolution, 0, 
                                                    origin[0], 0, 
                                                    -resolution, origin[1])
    new_profile['crs'] = profile['crs']
    new_profile['height'] = height
    new_profile['width'] = width
    new_profile['count'] = 5
    new_profile['dtype'] = 'uint8'
    new_profile['driver'] = 'GTiff'
    new_profile['compress'] = 'deflate'
    new_profile['interleave'] = 'band'
    new_profile['tiled'] = True
    new_profile['blockxsize'] = 256
    new_profile['blockysize'] = 256

    request = {
        'expression': naip_mosaic,
        'fileFormat': 'NUMPY_NDARRAY',
        'grid': {
            'dimensions': {
                'width': height,
                'height': width
            },
            'affineTransform': {
                'scaleX': resolution,
                'shearX': 0,
                'translateX': origin[0],
                'scaleY': -resolution,
                'shearY': 0,
                'translateY': origin[1]
            },
            'crsCode': new_profile['crs'].to_string(),
        },
    }

    image = ee.data.computePixels(request)
    image = image.view((np.uint8, len(image.dtype.names)))
    image = np.transpose(image, (2, 0, 1))

    naip_file = '_'.join(file_info) + '_' + naip_dict['start_date'] + '.tif'
    naip_file_status = naip_file.replace('/naip/', '/naip-status/')

    with rio.open(naip_file, 'w', **new_profile) as dst:
        dst.write(image)
    
    return None

# Example for a sample location south of Myton, UT
naip('12_580020_4445973_2018-04-21.tif')