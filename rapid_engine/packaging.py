"""Independent raster packaging primitives, not a hydraulic simulator."""
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import reproject, Resampling, transform_geom

NODATA=-9999.0

def write_derivative(native, valid, native_transform, native_crs, reference_path, output, *, arrival_seconds=False):
    """Nearest mapping preserves explicit native domain; dry zero must be input evidence."""
    native=np.asarray(native,dtype='float32');valid=np.asarray(valid,dtype=bool)
    if native.ndim!=2 or valid.shape!=native.shape:raise ValueError('Native grid/mask mismatch')
    if not valid.any() or not np.isfinite(native[valid]).all() or (native[valid]<0).any():raise ValueError('Invalid physical product')
    values=np.where(valid,native,NODATA).astype('float32')
    if arrival_seconds:
        values[valid]=np.ceil(values[valid]/3600)*60
    with rasterio.open(reference_path) as ref:
        if str(ref.crs)!='EPSG:32643' or ref.transform.b!=0 or ref.transform.d!=0:raise ValueError('Unsupported target grid')
        dest=np.full((ref.height,ref.width),NODATA,dtype='float32')
        reproject(values,dest,src_transform=native_transform,src_crs=native_crs,src_nodata=NODATA,
            dst_transform=ref.transform,dst_crs=ref.crs,dst_nodata=NODATA,resampling=Resampling.nearest)
        with rasterio.open(output,'w',driver='GTiff',width=ref.width,height=ref.height,count=1,dtype='float32',crs=ref.crs,
            transform=ref.transform,nodata=NODATA,tiled=True,blockxsize=256,blockysize=256,compress='deflate',
            predictor=1,BIGTIFF='NO',ENDIANNESS='LITTLE') as ds:ds.write(dest,1)
    return dest

def extent_from_depth(depth_path, output):
    with rasterio.open(depth_path) as ds:
        depth=ds.read(1);valid=np.isfinite(depth)&(depth!=ds.nodata);wet=valid&(depth>0.1)
        features=[]
        for geom,value in shapes(wet.astype('uint8'),mask=wet,transform=ds.transform):
            if value:
                features.append({'type':'Feature','properties':{'threshold_m':0.1},
                    'geometry':transform_geom(ds.crs,'EPSG:4326',geom)})
    Path(output).write_text(json.dumps({'type':'FeatureCollection','features':features},allow_nan=False),encoding='utf-8')
    return int(wet.sum())
