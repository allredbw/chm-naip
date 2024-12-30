library(stringr)
library(lidR)
library(terra)
library(lutz)


chm_create <- function(filename) {

  matches <- stringr::str_match_all(filename, '(?<=/|_)([\\d-]+)')

  utm_zone <- as.numeric(matches[[1]][,2][1])
  utm_crs <- paste('EPSG:', (32600 + utm_zone), sep='')

  x <- as.numeric(matches[[1]][,2][2])
  y <- as.numeric(matches[[1]][,2][3])

  lidR::set_lidr_threads(2)
  
  las <- lidR::readLAS(filename, filter='-drop_withheld -drop_class 7 18')
  if (lidR::is.empty(las)) return(paste(filename, 'error empty-las'))
  
  las_extent <- lidR::st_bbox(las)
  if ((x < las_extent$xmin) | (x > las_extent$xmax) | 
      (y < las_extent$ymin) | (y > las_extent$ymax)) return(paste(filename, 'error extent'))
  
  ground <- lidR::filter_poi(las, (Classification == 2))
  if (lidR::is.empty(ground)) return(paste(filename, 'error empty-ground'))
  
  las <- lidR::classify_noise(las, lidR::ivf(res = 5, n = 6))
  if (lidR::is.empty(las)) return(paste(filename, 'error empty-noise'))
  
  las <- lidR::filter_poi(las, Classification != 18)
  if (lidR::is.empty(las)) return(paste(filename, 'error empty-noise'))
  
  nlas <- lidR::normalize_height(las, lidR::knnidw())
  if (lidR::is.empty(nlas)) return(paste(filename, 'error empty-normalize'))
  
  nlas <- lidR::filter_poi(nlas, Z>=0 & Z<300)
  if (lidR::is.empty(nlas)) return(paste(filename, 'error empty-filter'))
  
  chm <- try(lidR::rasterize_canopy(las = nlas,
                                    res = 1,
                                    algorithm = lidR::pitfree(
                                      thresholds = c(0, 2, 5, 10, 15),
                                      max_edge = c(10, 1),
                                      subcircle = 0.35
                                    )
  ))
  
  if (inherits(chm, "try-error")) {
    chm <- lidR::rasterize_canopy(las = nlas,
                                  res = 1,
                                  algorithm = lidR::p2r(subcircle = 0.35))
  } else if (inherits(chm, "try-error")) {
    return(paste(filename, 'error chm'))
  }
  
  point <- terra::vect(data.frame(x = x, y = y),
                       geom = c('x', 'y'),
                       crs = utm_crs)
  point <- terra::project(point, chm)
  
  point_buffer <- terra::buffer(point, 128)
  buffer_extent <- terra::ext(point_buffer)
  chm <- terra::extend(chm, buffer_extent)
  
  row_col <- terra::rowColFromCell(chm, terra::extract(chm, point, cells=TRUE)$cell)
  row_center <- row_col[1]
  col_center <- row_col[2]
  
  chm <- chm[(row_center-128):(row_center+127),
             (col_center-128):(col_center+127),
             drop=FALSE]
  
  chm <- chm * 100
  
  
  gps_time <- try(min(nlas$gpstime) + 1e9)
  
  if (inherits(gps_time, "try-error")) {
    date <- '_XXXX-XX-XX.tif'
    filename_tif_new <- stringr::str_replace(filename, '\\.laz', date)
  } else if ((gps_time - 1e9) <= 604800) {
    date <- '_XXXX-XX-XX.tif'
    filename_tif_new <- stringr::str_replace(filename, '\\.laz', date)
  } else {
    date <- as.POSIXct(as.POSIXct("1980-01-06 00:00:00.000",  tz = 'UTC') + gps_time)
    tz <- lutz::tz_lookup(sf::st_as_sf(point))
    date <- as.character(as.Date(as.POSIXct(date, tz = tz)))
    filename_tif_new <- paste(utm_zone, '_', x, '_', y, '_', date, '.tif', sep='')
  }
  
  terra::writeRaster(x = chm,
                     filename = filename_tif_new,
                     datatype = 'INT2U',
                     NAflag = 65535,
                     gdal = c('compress=deflate', 'tiled=yes',
                              'blockxsize=256', 'blockysize=256'),
                     overwrite = TRUE)
  
  return(paste(filename_tif_new, 'created'))
  
}

# Example for a sample location south of Myton, UT
chm_create('12_580020_4445973_2018-04-27_2018-06-02.laz')
