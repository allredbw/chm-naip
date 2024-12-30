Code for the paper "Canopy height model and NAIP imagery pairs across CONUS". The
basic workflow consisted of 1) [PDAL](http://pdal.io/) to retreive lidar points
from an AWS cloud storage bucket; 2) [lidR](https://github.com/r-lidar/lidR) to
produce the canopy height model (CHM); and 3) [Google Earth
Engine](https://earthengine.google.com/) to produce the NAIP imagery composite. 

1. laz.py - Python function to retrieve lidar points.
2. chm.R - R function to generate CHM.
3. naip.py - Python function to produce NAIP composite.

This workflow was used to produce 22,796,764 spatially matching CHM and NAIP
pairs. Data are available at http://rangeland.ntsg.umt.edu/data/rap/chm-naip/. 


Citation:  
Allred, B.W., S.E. McCord, and S.L. Morford. 2024. Canopy height model and NAIP
imagery pairs across CONUS. bioRxiv. http://dx.doi.org/10.1101/2024.12.24.630202