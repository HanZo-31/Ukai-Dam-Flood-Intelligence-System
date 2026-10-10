from pathlib import Path
import sys
import json
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rapid_engine.packaging import write_derivative,extent_from_depth

def target(tmp_path):
    path=tmp_path/'target.tif'
    with rasterio.open(path,'w',driver='GTiff',height=2,width=2,count=1,dtype='float32',crs='EPSG:32643',
        transform=from_origin(270000,2360000,100,100),nodata=-9999) as ds:ds.write(np.zeros((2,2),dtype='float32'),1)
    return path

def test_preserve_unknown_and_known_dry(tmp_path):
    out=tmp_path/'depth.tif';transform=from_origin(270000,2360000,100,100)
    depth=write_derivative([[0,5],[4,999]],[[True,True],[True,False]],transform,'EPSG:32643',target(tmp_path),out)
    assert depth.tolist()==[[0,5],[4,-9999]]
    with rasterio.open(out) as ds:assert ds.block_shapes==[(256,256)] and ds.nodata==-9999 and str(ds.crs)=='EPSG:32643'
    extent=tmp_path/'extent.json';assert extent_from_depth(out,extent)==2
    assert len(json.loads(extent.read_text())['features'])==2

def test_arrival_once_hourly_ceiling(tmp_path):
    depth=write_derivative([[0,3600],[3601,7200]],np.ones((2,2),bool),from_origin(270000,2360000,100,100),
        'EPSG:32643',target(tmp_path),tmp_path/'arrival.tif',arrival_seconds=True)
    assert depth.tolist()==[[0,60],[120,120]]

@pytest.mark.parametrize('data,valid',[([[-1]],[[True]]),([[float('nan')]],[[True]]),([[1]],[[False]]),([[1]],[[True,False]])])
def test_invalid_native(tmp_path,data,valid):
    with pytest.raises(ValueError):write_derivative(data,valid,from_origin(270000,2360000,100,100),'EPSG:32643',target(tmp_path),tmp_path/'out.tif')
