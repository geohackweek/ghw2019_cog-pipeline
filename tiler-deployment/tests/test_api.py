import os
import json
import base64

import pytest

import vector_tile_base
from tiler.api import APP

file_sar = os.path.join(os.path.dirname(__file__), "fixtures", "sar_cog.tif")
file_rgb = os.path.join(os.path.dirname(__file__), "fixtures", "rgb_cog.tif")
file_lidar = os.path.join(os.path.dirname(__file__), "fixtures", "lidar_cog.tif")
file_nodata = os.path.join(os.path.dirname(__file__), "fixtures", "rgb_cog_nodata.tif")

file_mos1 = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic_cog1.tif")
file_mos2 = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic_cog2.tif")
mosaic_url = ",".join([file_mos1, file_mos2])


@pytest.fixture()
def event():
    """event fixture"""
    return {
        "path": "/",
        "httpMethod": "GET",
        "headers": {},
        "queryStringParameters": {},
    }


def test_API_favicon(event):
    """Test /favicon.ico route."""

    event["path"] = "/favicon.ico"
    event["httpMethod"] = "GET"

    resp = {
        "body": "",
        "headers": {
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "text/plain",
        },
        "statusCode": 204,
    }
    res = APP(event, {})
    assert res == resp


def test_API_bbox(event):
    """Test /bbox route."""
    event["path"] = f"/bbox"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert "url" in body["errorMessage"]
    assert "bbox" in body["errorMessage"]
    print(body["errorMessage"])

    event["path"] = f"/bbox"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_rgb}
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert "bbox" in body["errorMessage"]

    event["path"] = f"/bbox"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_rgb,
        "bbox": "-61.56544,-61.563559,16.226925",
    }
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["errorMessage"] == "BBOX must be a 4 values array"

    event["path"] = f"/bbox"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_rgb,
        "bbox": "-61.56544,16.22859,-61.563559,16.226925",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert body["bbox"]
    assert body["band_descriptions"]
    assert len(body["statistics"].keys()) == 3

    event["path"] = f"/bbox"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_rgb,
        "indexes": "1,2",
        "bbox": "-61.56544,16.22859,-61.563559,16.226925",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["statistics"].keys()) == 2

    event["path"] = f"/bbox"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_nodata,
        "nodata": "0",
        "histogram_bins": "10",
        "bbox": "-104.77514,38.9536719,-104.7749354,38.9535883",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert len(body["statistics"]["1"]["histogram"][0]) == 10

    # Test boox outside data
    event["path"] = f"/bbox"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_nodata,
        "nodata": "0",
        "bbox": "-61.56544,16.22859,-61.563559,16.226925",
    }
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"


def test_API_point(event):
    """Test /point route."""
    event["path"] = f"/point"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert "url" in body["errorMessage"]

    event["path"] = f"/point"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_rgb}
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert "coordinates" in body["errorMessage"]

    event["path"] = f"/point"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_rgb,
        "coordinates": "-61.56463623161228,16.227860775481847",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert body["band_descriptions"]
    assert len(body["coordinates"]) == 2
    assert body["values"] == {"1": 82, "2": 126, "3": 99}

    # Test indexes
    event["queryStringParameters"] = {
        "url": file_rgb,
        "coordinates": "-61.56463623161228,16.227860775481847",
        "indexes": "2",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    body = json.loads(res["body"])
    assert body["address"]
    assert body["band_descriptions"]
    assert len(body["coordinates"]) == 2
    assert body["values"] == {"2": 126}


def test_API_metadata(event):
    """Test /metadata route."""
    event["path"] = f"/metadata"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert "url" in body["errorMessage"]

    event["path"] = f"/metadata"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_sar}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["bounds"]["value"]) == 4
    assert body["bounds"]["crs"] == "EPSG:4326"
    assert len(body["statistics"].keys()) == 1
    assert body["minzoom"]
    assert body["maxzoom"]
    assert body["band_descriptions"]

    event["path"] = f"/metadata"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_lidar, "histogram_bins": "20"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["bounds"]["value"]) == 4
    assert body["bounds"]["crs"] == "EPSG:4326"
    assert len(body["statistics"]['1']["histogram"][0]) == 20
    assert body["minzoom"]
    assert body["maxzoom"]
    assert body["band_descriptions"] == [
        [1, 'min'], [2, 'max'], [3, 'mean'], [4, 'idw'], [5, 'stdev']
    ]

    event["path"] = f"/metadata"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_rgb}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["bounds"]["value"]) == 4
    assert body["bounds"]["crs"] == "EPSG:4326"
    assert len(body["statistics"].keys()) == 3
    assert body["minzoom"]
    assert body["maxzoom"]
    assert body["band_descriptions"]

    event["queryStringParameters"] = {"url": file_nodata, "nodata": "0"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["bounds"]["value"]) == 4
    assert body["bounds"]["crs"] == "EPSG:4326"
    assert len(body["statistics"].keys()) == 3

    event["queryStringParameters"] = {"url": file_rgb, "indexes": "1"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["bounds"]["value"]) == 4
    assert body["bounds"]["crs"] == "EPSG:4326"
    assert len(body["statistics"].keys()) == 1

    event["queryStringParameters"] = {"url": file_rgb, "overview_level": "1"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["bounds"]["value"]) == 4
    assert body["bounds"]["crs"] == "EPSG:4326"
    assert len(body["statistics"].keys()) == 3

    event["queryStringParameters"] = {"url": file_rgb, "max_size": "512"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["address"]
    assert len(body["bounds"]["value"]) == 4
    assert body["bounds"]["crs"] == "EPSG:4326"
    assert len(body["statistics"].keys()) == 3


def test_API_tiles(event):
    """Test /tiles route."""
    # test missing url in queryString
    event["path"] = f"/tiles/12/2180/2049.jpg"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["errorMessage"] == "Missing 'url' parameter"

    # test valid jpg request with linear rescaling
    event["path"] = f"/tiles/12/2180/2049.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_sar, "rescale": "-1,1"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test valid jpg request with rescaling and colormap
    event["path"] = f"/tiles/12/2180/2049.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_sar,
        "rescale": "-1,1",
        "color_map": "cfastie",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test scale (512px tile size)
    event["path"] = f"/tiles/12/2180/2049@2x.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_sar, "rescale": "-1,1"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test with nodata == nan
    event["path"] = f"/tiles/12/2180/2049.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_sar,
        "rescale": "-1,1",
        "nodata": "nan",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test internal nodata
    event["path"] = f"/tiles/20/219109/400917.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_nodata, "rescale": "0,2000"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test rgb file
    event["path"] = f"/tiles/18/86242/119093.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_rgb}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test indexes option
    event["path"] = f"/tiles/18/86242/119093.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_rgb, "indexes": "1"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test colormap
    event["path"] = f"/tiles/18/86242/119093.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_rgb, "color_ops": "gamma rgb 3"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]


def test_API_tilejson(event):
    """Test /metadata route."""
    event["path"] = f"/tilejson.json"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert "url" in body["errorMessage"]

    event["path"] = f"/tilejson.json"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_sar}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["name"] == os.path.basename(file_sar)
    assert body["tilejson"] == "2.1.0"
    assert body["tiles"]
    assert body["tiles"][0].endswith(f"{{z}}/{{x}}/{{y}}.png?url={file_sar}")
    assert len(body["bounds"]) == 4
    assert len(body["center"]) == 2
    assert body["minzoom"] == 9
    assert body["maxzoom"] == 10

    event["path"] = f"/tilejson.json"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_sar, "tile_format": "pbf"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["name"] == os.path.basename(file_sar)
    assert body["tilejson"] == "2.1.0"
    assert body["tiles"]
    assert body["tiles"][0].endswith(f"{{z}}/{{x}}/{{y}}.pbf?url={file_sar}")
    assert len(body["bounds"]) == 4
    assert len(body["center"]) == 2
    assert body["minzoom"] == 9
    assert body["maxzoom"] == 10

    # test with kwargs and image_format
    event["path"] = f"/tilejson.json"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_sar, "tile_format": "jpg", "rescale": "-1,1"
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["name"] == os.path.basename(file_sar)
    assert body["tilejson"] == "2.1.0"
    assert body["tiles"]
    assert body["tiles"][0].endswith(f"{{z}}/{{x}}/{{y}}.jpg?url={file_sar}&rescale=-1,1")
    assert len(body["bounds"]) == 4
    assert len(body["center"]) == 2
    assert body["minzoom"] == 9
    assert body["maxzoom"] == 10


def test_API_Vtiles(event):
    """Test /tiles.pbf route."""
    # test missing url in queryString
    event["path"] = f"/tiles/12/2161/2047.pbf"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert "url" in body["errorMessage"]

    event["path"] = f"/tiles/12/2161/2047.pbf"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"url": file_lidar}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/x-protobuf"
    assert res["body"]
    assert res["isBase64Encoded"]
    body = base64.b64decode(res["body"])

    vt = vector_tile_base.VectorTile(body)
    props = vt.layers[0].features[0].properties
    assert props["min"]
    assert props["min"] == "11.0"

    event["path"] = f"/tiles/12/2161/2047.pbf"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "url": file_lidar,
        "nodata": "-9999",
        "feature_type": "polygon"
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/x-protobuf"
    assert res["body"]
    assert res["isBase64Encoded"]
    body = base64.b64decode(res["body"])

    vt = vector_tile_base.VectorTile(body)
    props = vt.layers[0].features[0].properties
    assert props["min"]
    assert props["max"]
    assert props["mean"]
    assert props["idw"]


def test_API_tilejson_mosaic(event):
    """Test /mosaic/tilejson.json route."""
    # test missing url in queryString
    event["path"] = f"/mosaic/tilejson.json"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500

    # test valid jpg request with linear rescaling
    event["path"] = f"/mosaic/tilejson.json"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"urls": mosaic_url, "rescale": "-1,1"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["bounds"]
    assert body["minzoom"] == 9
    assert body["maxzoom"] == 11


def test_API_tiles_mosaic(event):
    """Test /mosaic route."""
    # test missing url in queryString
    event["path"] = f"/mosaic/12/2156/2041.jpg"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 500
    headers = res["headers"]
    assert headers["Content-Type"] == "application/json"
    body = json.loads(res["body"])
    assert body["errorMessage"] == "Missing 'urls' parameter"

    # test valid jpg request with linear rescaling
    event["path"] = f"/mosaic/12/2156/2041.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"urls": mosaic_url, "rescale": "-1,1"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test valid jpg request with rescaling and colormap
    event["path"] = f"/mosaic/12/2156/2041.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "urls": mosaic_url,
        "rescale": "-1,1",
        "color_map": "cfastie",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test scale (512px tile size)
    event["path"] = f"/mosaic/12/2156/2041@2x.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"urls": mosaic_url, "rescale": "0,10"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test with nodata == nan
    event["path"] = f"/mosaic/12/2156/2041.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "urls": mosaic_url,
        "rescale": "-1,1",
        "nodata": "nan",
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test indexes option
    event["path"] = f"/mosaic/12/2156/2041.jpg"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {
        "urls": mosaic_url, "indexes": "1", "rescale": "0,10"
    }
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/jpg"
    assert res["body"]
    assert res["isBase64Encoded"]

    # test mvt option
    event["path"] = f"/mosaic/12/2156/2041.pbf"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"urls": mosaic_url}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/x-protobuf"
    assert res["body"]
    assert res["isBase64Encoded"]
    body = base64.b64decode(res["body"])

    vt = vector_tile_base.VectorTile(body)
    props = vt.layers[0].features[0].properties
    assert props["idw"]

    # test mvt option
    event["path"] = f"/mosaic/12/2156/2041.pbf"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {"urls": mosaic_url, "feature_type": "polygon"}
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/x-protobuf"
    assert res["body"]
    assert res["isBase64Encoded"]
    body = base64.b64decode(res["body"])

    vt = vector_tile_base.VectorTile(body)
    props = vt.layers[0].features[0].properties
    assert props["idw"]
