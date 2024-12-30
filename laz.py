import os
import json

import pdal
import geopandas as gpd

def laz(x, y, zone, collect_start, collect_end, url):
    """
    
    Writes LAZ file of lidar points within a 200m radius square buffer around
    specified point. LAZ is projected to UTM NAD83.
    
    Args:
        x (int): x coordinate (UTM easting); WGS84
        y (int): y coordinate (UTM northing); WGS84
        zone (int): UTM zone
        collect_start (str): collection start date; for file naming
        collect_end (str): collection end date; for file naming
        url (str): url for ept.json file
    """

    buffer_size = 200

    filename = (str(zone) + '_' + str(x) + '_' + str(y) + '_' + 
                str(collect_start) + '_' + str(collect_end) + '.laz')
        
    utm_crs_in = 'EPSG:' + str(32600 + zone)
    utm_crs_out = 'EPSG:' + str(26900 + zone)
    
    geometry_utm = gpd.points_from_xy([x], [y], crs = utm_crs_in)
    geometry_3857 = geometry_utm.to_crs("EPSG:3857")
    geometry_buffered = geometry_3857.buffer(buffer_size, cap_style = 3)

    reader = [{
        "type": "readers.ept",
        "filename": str(url),
        "polygon": str(geometry_buffered[0]),
        "resolution": 1
    }]

    pipeline = {"pipeline": reader}

    filter_stage = {
        "type": "filters.range",
        "limits": "Classification![7:7], Classification![18:18]"
    }

    pipeline['pipeline'].append(filter_stage)

    reprojection_stage = {
        "type": "filters.reprojection",
        "out_srs": utm_crs_out
    }

    pipeline['pipeline'].append(reprojection_stage)

    save_stage = {
        "type": "writers.las",
        "compression": "laszip",
        "filename": filename
    }
    
    pipeline['pipeline'].append(save_stage)
        
    pdal.Pipeline(json.dumps(pipeline)).execute_streaming(chunk_size=1000000)
    
    return None


# Example for a sample location south of Myton, UT
laz(580020, 4445973, 12, '2018-04-27', '2018-06-02', 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_UT_FemaHQ_B1_TL_2018_LAS_2019/ept.json')