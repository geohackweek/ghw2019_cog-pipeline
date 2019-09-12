"""app: handle request for tiler."""

import os
import re
import json
from concurrent import futures

import numpy

import rasterio
from rasterio import warp

from rio_tiler import main
from rio_tiler.utils import (
    array_to_image,
    get_colormap,
    linear_rescale,
    mapzen_elevation_rgb,
)
from rio_tiler.profiles import img_profiles
from rio_tiler.mercator import get_zooms
from rio_tiler_mosaic.mosaic import mosaic_tiler
from rio_tiler_mvt.mvt import encoder as mvtEncoder

from rio_rgbify import encoders
from rio_color.operations import parse_operations
from rio_color.utils import scale_dtype, to_math_type

from .utils import get_area_stats

from lambda_proxy.proxy import API

APP = API(name="tiler")

class TilerError(Exception):
    """Base exception class."""

@APP.route(
    "/metadata",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
def meta(
    url,
    nodata=None,
    indexes=None,
    overview_level=None,
    max_size=1024,
    histogram_bins=20,
    histogram_range=None,
):
    """
    Handle /metadata requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    url : str, required
        Dataset url to read from.
    nodata, str, optional
        Custom nodata value if not preset in dataset.
    indexes : str, optional, (defaults: None)
        Comma separated band index number (e.g "1,2,3").
    overview_level, str, optional
        Select the overview level to fetch for statistic calculation.
        By default if will grabb the one closer to the `max_size` value.
    max_size: str, optional
        Maximum size of dataset to retrieve
        (will be used to calculate the overview level to fetch).
    histogram_bins: int, optional
        Defines the number of equal-width histogram bins (default: 20).
    histogram_range: str, optional
        The lower and upper range of the bins. If not provided, range is simply
        the min and max of the array.

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. image/jpeg).
    body : str
        String encoded json statistic metadata.

    """
    if indexes is not None and isinstance(indexes, str):
        indexes = tuple(int(s) for s in re.findall(r"\d+", indexes))

    if overview_level is not None and isinstance(overview_level, str):
        overview_level = int(overview_level)

    if nodata is not None and isinstance(nodata, str):
        nodata = numpy.nan if nodata == "nan" else float(nodata)

    if max_size is not None and isinstance(max_size, str):
        max_size = int(max_size)

    if histogram_bins is not None and isinstance(histogram_bins, str):
        histogram_bins = int(histogram_bins)

    if histogram_range is not None and isinstance(histogram_range, str):
        histogram_range = tuple(map(float, histogram_range.split(",")))

    info = main.metadata(
        url,
        nodata=nodata,
        indexes=indexes,
        overview_level=overview_level,
        histogram_bins=histogram_bins,
        histogram_range=histogram_range,
    )

    return ("OK", "application/json", json.dumps(info))


@APP.route(
    "/bbox",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
def bbox_stats(
    url,
    bbox,
    nodata=None,
    indexes=None,
    histogram_bins=20,
    histogram_range=None,
):
    """
    Handle /bbox requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    url : str, required
        Dataset url to read from.
    bbox : str, required
        Comma separated "left, bottom, right, top" values.
    nodata, str, optional
        Custom nodata value if not preset in dataset.
    indexes : str, optional, (defaults: None)
        Comma separated band index number (e.g "1,2,3").
    histogram_bins: int, optional
        Defines the number of equal-width histogram bins (default: 20).
    histogram_range: str, optional
        The lower and upper range of the bins. If not provided, range is simply
        the min and max of the array.

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. image/jpeg).
    body : bytes
        String encoded bbox json statistic metadata.

    """
    bbox = list(map(float, bbox.split(",")))
    if len(bbox) != 4:
        raise Exception("BBOX must be a 4 values array")

    if indexes is not None and isinstance(indexes, str):
        indexes = tuple(int(s) for s in re.findall(r"\d+", indexes))

    if nodata is not None and isinstance(nodata, str):
        nodata = numpy.nan if nodata == "nan" else float(nodata)

    if histogram_bins is not None and isinstance(histogram_bins, str):
        histogram_bins = int(histogram_bins)

    if histogram_range is not None and isinstance(histogram_range, str):
        histogram_range = tuple(map(float, histogram_range.split(",")))

    stats, band_descriptions = get_area_stats(
        url,
        bbox,
        nodata=nodata,
        indexes=indexes,
        histogram_bins=histogram_bins,
        histogram_range=histogram_range,
    )
    if not stats:
        raise TilerError("BBOX outside raster bounds")

    return (
        "OK",
        "application/json",
        json.dumps({
            "address": url,
            "bbox": bbox,
            "band_descriptions": band_descriptions,
            "statistics": stats,
        }),
    )


@APP.route(
    "/point",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
def point_value(url, coordinates, indexes=None):
    """
    Handle /point requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    url : str, required
        Dataset url to read from.
    coordinates : str, required
        Comma separated longitude,latitude values.
    indexes : str, optional, (defaults: None)
        Comma separated band index number (e.g "1,2,3").

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. image/jpeg).
    body : bytes
        String encoded json point value

    """
    if indexes is not None and isinstance(indexes, str):
        indexes = tuple(int(s) for s in re.findall(r"\d+", indexes))

    coordinates = list(map(float, coordinates.split(",")))
    with rasterio.open(url) as src_dst:
        indexes = indexes if indexes is not None else src_dst.indexes
        lon_srs, lat_srs = warp.transform(
            "EPSG:4326", src_dst.crs, [coordinates[0]], [coordinates[1]]
        )
        results = list(src_dst.sample([(lon_srs[0], lat_srs[0])], indexes=indexes))[0]

        def _get_name(idx):
            name = src_dst.descriptions[idx - 1]
            if not name:
                name = f"band{idx}"
            return name

        band_descriptions = [(ix, _get_name(ix)) for ix in indexes]

    return (
        "OK",
        "application/json",
        json.dumps(
            {
                "address": url,
                "coordinates": coordinates,
                "band_descriptions": band_descriptions,
                "values": {b[0]: r for b, r in zip(band_descriptions, results.tolist())}
            }
        ),
    )


@APP.route(
    "/tilejson.json",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
@APP.pass_event
def tilejson(request, url, tile_format="png", **kwargs):
    """
    Handle /tilejson.json requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    url : str, required
        Dataset url to read from.
    image_format : str
        Image format to return (default: png).
    kwargs: dict, optional
        Querystring parameters to forward to the tile url.

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. application/json).
    body : str
        String encoded TileJSON.

    """
    host = request["headers"].get(
        "X-Forwarded-Host", request["headers"].get("Host", "")
    )
    # Check for API gateway stage
    if ".execute-api." in host and ".amazonaws.com" in host:
        stage = request["requestContext"].get("stage", "")
        host = f"{host}/{stage}"

    scheme = "http" if host.startswith("127.0.0.1") else "https"

    qs = [f"{k}={v}" for k, v in kwargs.items()]
    qs = "&".join(qs)

    tile_url = f"{scheme}://{host}/tiles/{{z}}/{{x}}/{{y}}.{tile_format}?url={url}"
    if qs:
        tile_url += f"&{qs}"

    with rasterio.open(url) as src_dst:
        bounds = warp.transform_bounds(
            *[src_dst.crs, "epsg:4326"] + list(src_dst.bounds), densify_pts=21
        )
        center = [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2]
        minzoom, maxzoom = get_zooms(src_dst)

    meta = dict(
        bounds=bounds,
        center=center,
        minzoom=minzoom,
        maxzoom=maxzoom,
        name=os.path.basename(url),
        tilejson="2.1.0",
        tiles=[tile_url]
    )

    return ("OK", "application/json", json.dumps(meta))


def _get_layer_names(src_path):
    with rasterio.open(src_path) as src_dst:
        def _get_name(ix):
            name = src_dst.descriptions[ix - 1]
            if not name:
                name = f"band{ix}"
            return name
        return [_get_name(ix) for ix in src_dst.indexes]


@APP.route(
    "/tiles/<int:z>/<int:x>/<int:y>.pbf",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
def mvt(
    z,
    x,
    y,
    url,
    scale=1,
    nodata=None,
    feature_type="point",
    resampling="nearest",
):
    """
    Handle MVT /tiles requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    z : int, required
        Mercator tile ZOOM level.
    x : int, required
        Mercator tile X index.
    y : int, required
        Mercator tile Y index.
    url : str, required
        Dataset url to read from.
    scale : int
        Output scale factor (default: 1).
    nodata : str, optional
        Custom nodata value if not preset in dataset.
    feature_type : str, optional
        Output feature type (default: point)
    resampling : str, optional
        Data resampling (default: nearest)

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. application/x-protobuf).
    body : bytes
        VT body.

    """
    if nodata is not None and isinstance(nodata, str):
        nodata = numpy.nan if nodata == "nan" else float(nodata)

    tilesize = 256 * scale

    tile, mask = main.tile(
        url,
        x,
        y,
        z,
        tilesize=tilesize,
        nodata=nodata,
        resampling_method=resampling,
    )

    band_descriptions = _get_layer_names(url)

    return (
        "OK",
        "application/x-protobuf",
        mvtEncoder(
            tile,
            mask,
            band_descriptions,
            os.path.basename(url),
            feature_type=feature_type,
        ),
    )


def _postprocess_tile(tile, mask, rescale=None, color_ops=None):
    """Tile data post-processing."""
    if rescale:
        rescale = (tuple(map(float, rescale.split(","))),) * tile.shape[0]
        for bdx in range(tile.shape[0]):
            tile[bdx] = numpy.where(
                mask,
                linear_rescale(tile[bdx], in_range=rescale[bdx], out_range=[0, 255]),
                0,
            )
        tile = tile.astype(numpy.uint8)

    if color_ops:
        # make sure one last time we don't have
        # negative value before applying color formula
        tile[tile < 0] = 0
        for ops in parse_operations(color_ops):
            tile = scale_dtype(ops(to_math_type(tile)), numpy.uint8)

    return tile, mask


@APP.route(
    "/tiles/<int:z>/<int:x>/<int:y>.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
@APP.route(
    "/tiles/<int:z>/<int:x>/<int:y>@<int:scale>x.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
def tiles(
    z,
    x,
    y,
    scale=1,
    ext="png",
    url=None,
    nodata=None,
    indexes=None,
    rescale=None,
    color_ops=None,
    color_map=None,
    dem=None,
):
    """
    Handle Raster /tiles requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    z : int, required
        Mercator tile ZOOM level.
    x : int, required
        Mercator tile X index.
    y : int, required
        Mercator tile Y index.
    scale : int
        Output scale factor (default: 1).
    ext : str
        Image format to return (default: png).
    url : str, required
        Dataset url to read from.
    indexes : str, optional, (defaults: None)
        Comma separated band index number (e.g "1,2,3").
    nodata, str, optional
        Custom nodata value if not preset in dataset.
    rescale : str, optional
        Min and Max data bounds to rescale data from.
    color_ops : str, optional
        rio-color compatible color formula
    color_map : str, optional
        Rio-tiler compatible colormap name ("cfastie" or "schwarzwald")
    dem : str, optional
        Create Mapbox or Mapzen RGBA encoded elevation image

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. image/jpeg).
    body : bytes
        Image body.

    """
    if not url:
        raise TilerError("Missing 'url' parameter")

    if indexes:
        indexes = tuple(int(s) for s in re.findall(r"\d+", indexes))

    if nodata is not None and isinstance(nodata, str):
        nodata = numpy.nan if nodata == "nan" else float(nodata)

    tilesize = 256 * scale

    tile, mask = main.tile(
        url, x, y, z, indexes=indexes, tilesize=tilesize, nodata=nodata
    )

    if dem:
        if dem == "mapbox":
            tile = encoders.data_to_rgb(tile, -10000, 1)
        elif dem == "mapzen":
            tile = mapzen_elevation_rgb.data_to_rgb(tile)
        else:
            return ("NOK", "text/plain", 'Invalid "dem" mode')
    else:
        rtile, rmask = _postprocess_tile(
            tile, mask, rescale=rescale, color_ops=color_ops
        )

        if color_map:
            color_map = get_colormap(color_map, format="gdal")

    driver = "jpeg" if ext == "jpg" else ext
    options = img_profiles.get(driver, {})
    return (
        "OK",
        f"image/{ext}",
        array_to_image(rtile, rmask, img_format=driver, color_map=color_map, **options),
    )


def _multiple_spatial_info(urls):
    def _get_info(url):
        with rasterio.open(url) as src_dst:
            wgs_bounds = warp.transform_bounds(
                *[src_dst.crs, "epsg:4326"] + list(src_dst.bounds), densify_pts=21
            )
            minzoom, maxzoom = get_zooms(src_dst)

        return {"bounds": list(wgs_bounds), "minzoom": minzoom, "maxzoom": maxzoom}

    with futures.ThreadPoolExecutor() as executor:
        all_infos = list(executor.map(_get_info, urls))

    minzoom = min(list(set([x["minzoom"] for x in all_infos])))
    maxzoom = max(list(set([x["maxzoom"] for x in all_infos])))

    left = min([x["bounds"][0] for x in all_infos])
    bottom = min([x["bounds"][1] for x in all_infos])
    right = max([x["bounds"][2] for x in all_infos])
    top = max([x["bounds"][3] for x in all_infos])
    bounds = [left, bottom, right, top]

    center = [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2]

    return {
        "bounds": bounds, "center": center, "minzoom": minzoom, "maxzoom": maxzoom
    }


@APP.route(
    "/mosaic/tilejson.json",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
@APP.pass_event
def mosaic_tilejson(request, urls, tile_format="png", **kwargs):
    """
    Handle /tilejson.json requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    urls : str, required
        Dataset url to read from.
    image_format : str
        Image format to return (default: png).
    kwargs: dict, optional
        Querystring parameters to forward to the tile url.

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. application/json).
    body : str
        String encoded TileJSON.

    """
    host = request["headers"].get(
        "X-Forwarded-Host", request["headers"].get("Host", "")
    )
    # Check for API gateway stage
    if ".execute-api." in host and ".amazonaws.com" in host:
        stage = request["requestContext"].get("stage", "")
        host = f"{host}/{stage}"

    scheme = "http" if host.startswith("127.0.0.1") else "https"

    qs = [f"{k}={v}" for k, v in kwargs.items()]
    qs = "&".join(qs)
    tile_url = f"{scheme}://{host}/mosaic/{{z}}/{{x}}/{{y}}.{tile_format}?urls={urls}"
    if qs:
        tile_url += f"&{qs}"

    info = _multiple_spatial_info(urls.split(','))

    meta = dict(
        bounds=info["bounds"],
        center=info["center"],
        minzoom=info["minzoom"],
        maxzoom=info["maxzoom"],
        tilejson="2.1.0",
        tiles=[tile_url]
    )

    return ("OK", "application/json", json.dumps(meta))


@APP.route(
    "/mosaic/<int:z>/<int:x>/<int:y>.pbf",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
def mosaic_tiles_mvt(
    z,
    x,
    y,
    scale=1,
    urls=None,
    nodata=None,
    pixel_selection: str = "first",
    resampling_method: str = "bilinear",
    feature_type="point",
):
    """
    Handle Raster /mosaics requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    z : int, required
        Mercator tile ZOOM level.
    x : int, required
        Mercator tile X index.
    y : int, required
        Mercator tile Y index.
    scale : int
        Output scale factor (default: 1).
    urls : str, required
        Dataset urls to read from.
    nodata, str, optional
        Custom nodata value if not preset in dataset.
    pixel_selection : str, optional
        rio-tiler-mosaic pixel selection method (default: first)
    resampling_method : str, optional
        Resampling method to use (default: bilinear)
    feature_type : str, optional
        Output feature type (default: point)

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. application/x-protobuf).
    body : bytes
        VT body.

    """
    if not urls:
        raise TilerError("Missing 'urls' parameter")

    if nodata is not None and isinstance(nodata, str):
        nodata = numpy.nan if nodata == "nan" else float(nodata)

    tilesize = 256 * scale
    tile, mask = mosaic_tiler(
        urls.split(","),
        x,
        y,
        z,
        main.tile,
        tilesize=tilesize,
        nodata=nodata,
        pixel_selection=pixel_selection,
        resampling_method=resampling_method,
    )
    if tile is None:
        return ("EMPTY", "text/plain", "empty tiles")

    band_descriptions = _get_layer_names(urls.split(",")[0])

    return (
        "OK",
        "application/x-protobuf",
        mvtEncoder(
            tile,
            mask,
            band_descriptions,
            "mosaic",
            feature_type=feature_type,
        ),
    )


@APP.route(
    "/mosaic/<int:z>/<int:x>/<int:y>.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
@APP.route(
    "/mosaic/<int:z>/<int:x>/<int:y>@<int:scale>x.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
)
def mosaic_tiles(
    z,
    x,
    y,
    scale=1,
    ext="png",
    urls=None,
    nodata=None,
    indexes=None,
    rescale=None,
    color_ops=None,
    color_map=None,
    pixel_selection: str = "first",
    resampling_method: str = "bilinear",
):
    """
    Handle Raster /mosaics requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    z : int, required
        Mercator tile ZOOM level.
    x : int, required
        Mercator tile X index.
    y : int, required
        Mercator tile Y index.
    scale : int
        Output scale factor (default: 1).
    ext : str
        Image format to return (default: png).
    urls : str, required
        Dataset urls to read from.
    indexes : str, optional, (defaults: None)
        Comma separated band index number (e.g "1,2,3").
    nodata, str, optional
        Custom nodata value if not preset in dataset.
    rescale : str, optional
        Min and Max data bounds to rescale data from.
    color_ops : str, optional
        rio-color compatible color formula
    color_map : str, optional
        Rio-tiler compatible colormap name ("cfastie" or "schwarzwald")
    pixel_selection : str, optional
        rio-tiler-mosaic pixel selection method (default: first)
    resampling_method : str, optional
        Resampling method to use (default: bilinear)

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. image/jpeg).
    body : bytes
        Image body.

    """
    if not urls:
        raise TilerError("Missing 'urls' parameter")

    if indexes:
        indexes = tuple(int(s) for s in re.findall(r"\d+", indexes))

    if nodata is not None and isinstance(nodata, str):
        nodata = numpy.nan if nodata == "nan" else float(nodata)

    tilesize = 256 * scale
    tile, mask = mosaic_tiler(
        urls.split(","),
        x,
        y,
        z,
        main.tile,
        indexes=indexes,
        tilesize=tilesize,
        nodata=nodata,
        pixel_selection=pixel_selection,
        resampling_method=resampling_method,
    )
    if tile is None:
        return ("EMPTY", "text/plain", "empty tiles")

    rtile, rmask = _postprocess_tile(tile, mask, rescale=rescale, color_ops=color_ops)

    if color_map:
        color_map = get_colormap(color_map, format="gdal")

    driver = "jpeg" if ext == "jpg" else ext
    options = img_profiles.get(driver, {})
    return (
        "OK",
        f"image/{ext}",
        array_to_image(rtile, rmask, img_format=driver, color_map=color_map, **options),
    )


@APP.route("/favicon.ico", methods=["GET"], cors=True)
def favicon():
    """Favicon."""
    return ("EMPTY", "text/plain", "")
