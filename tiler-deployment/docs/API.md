## API

### Get global dataset statistics
`/metadata` - GET

Inputs:
- **url** (required, str): dataset url
- **nodata** (optional, str): Custom nodata value if not preset in dataset.
- **indexes** (optional, str): dataset band indexes
- **overview_level** (optional, str): Select the overview level to fetch for statistic calculation
- **max_size** (optional, str): Maximum size of dataset to retrieve for overview level automatic calculation
- **histogram_bins** (optional, str, default:20): number of equal-width histogram bins
- **histogram_range** (optional, str): histogram min/max

Outputs:
- **metadata** (application/json)

`curl https://{endpoint-url}/metadata?url=s3://myfile.tif`

```js
{
    'bounds': {
        'value': [...],
        'crs': '+init=EPSG:4326'
    },
    'minzoom': 8,
    'maxzoom': 12,
    'band_descriptions': [(1, 'red'), (2, 'green'), (3, 'blue'), (4, 'nir')]
    'statistics': {
        '1': {
            'pc': [38, 147],
            'min': 20,
            'max': 180,
            'std': 28.123562304138662,
            'histogram': [
                [...],
                [...]
            ]
        },
        ...
    }
}
```

### Get dataset statistics over a bbox
`/bbox` - GET

Inputs:
- **url** (required, str): dataset url
- **bbox** (required, str): Comma separated "left, bottom, right, top" values
- **nodata** (optional, str): Custom nodata value if not preset in dataset.
- **indexes** (optional, str): dataset band indexes
- **histogram_bins** (optional, str, default: 20): number of equal-width histogram bins
- **histogram_range** (optional, str): histogram min/max

Outputs:
- **metadata** (application/json)

`curl https://{endpoint-url}/bbox?url=s3://myfile.tif&bbox=-1,-1,1,1`

```js
{
    'address': 's3://myfile.tif',
    'bbox': [...],
    'band_descriptions': [(1, 'red'), (2, 'green'), (3, 'blue'), (4, 'nir')]
    'statistics': {
        '1': {
            'pc': [38, 147],
            'min': 20,
            'max': 180,
            'std': 28.123562304138662,
            'histogram': [
                [...],
                [...]
            ]
        },
        ...
    }
}
```


### Get dataset pixel value over a point
`/point` - GET

Inputs:
- **url** (required, str): dataset url
- **coordinates** (required, str): Comma separated longitude,latitude values
- **indexes** (optional, str): dataset band indexes

Outputs:
- **metadata** (application/json)

`curl https://{endpoint-url}/point?url=s3://myfile.tif&coordinates=-1,-1`


```js
{
    'address': 's3://myfile.tif',
    'coordinates': [...],
    'band_descriptions': [(1, 'red'), (2, 'green'), (3, 'blue'), (4, 'nir')]
    'values': {
        '1': 0,
        '2': 1,
        '3': 2,
        '4': 3
    }
}
```

### TileJSON (2.1.0)
`/tilejson.json` - GET

Inputs:
- **url** (required): mosaic definition url
- **tile_format** (optional, str): output tile format (default: "png")
- **kwargs** (in querytring): tiler independant options (e.g "feature_type=point")

Outputs:
- **tileJSON** (application/json) 

```bash
$ curl https://{endpoint-url}/tilejson.json?url=s3://my_file.tif
```

```js
{
    "bounds": [...],      
    "center": [lon, lat], 
    "minzoom": 18,        
    "maxzoom": 22,        
    "name": "my_file.tif",
    "tilejson": "2.1.0",  
    "tiles": [...] ,      
}
```

### Get Mapbox Vector tiles
`/tiles/{z}/{x}/{y}.pbf` - GET

Inputs:
- **z** (path): Mercator tile zoom value
- **x** (path): Mercator tile x value
- **y** (path): Mercator tile y value
- **url** (required): mosaic definition url
- **scale** (optional, str): Tile scale (default: 1)
- **nodata** (optional, str): Custom nodata value if not preset in dataset.
- **feature_type** (optional, str): Vector Tile Feature type (default: `point`)
- **resampling** (optional, str): tiler resampling method (default: `nearest`)

Outputs:
- **protobuf** (application/x-protobuf)

```bash
$ curl https://{endpoint-url}/tiles/8/32/22.pbf?url=s3://my_file.tif
```

### Get Raster tiles
`/tiles/{z}/{x}/{y}.{ext}` - GET
`/tiles/{z}/{x}/{y}@{scale}x.{ext}` - GET

Inputs:
- **z** (path): Mercator tile zoom value
- **x** (path): Mercator tile x value
- **y** (path): Mercator tile y value
- **scale** (path, optional, str): tilesize scale (default: 1 for 256px)
- **ext** (path, str): image format (e.g `jpg`)
- **url** (required, str): dataset url
- **nodata** (optional, str): Custom nodata value if not preset in dataset.
- **indexes** (optional, str): dataset band indexes (default: None)
- **rescale** (optional, str): min/max for data rescaling (default: None)
- **color_ops** (optional, str): rio-color formula (default: None)
- **color_map** (optional, str): rio-tiler colormap (default: None)
- **dem** (optional, str): Create Mapbox or Mapzen RGBA encoded elevation image

Outputs:
- **image body** (e.g image/jpeg)

`curl https://{endpoint-url}/tiles/8/32/22.png?url=s3://myfile.tif`
