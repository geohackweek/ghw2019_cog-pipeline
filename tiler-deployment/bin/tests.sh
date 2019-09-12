#!/bin/bash
echo "Maap-tiler Version: " && python3.6 -c 'from tiler import version as version; print(version)'

echo "/bbox"
python3.6 -c 'from tiler.api import APP; resp = APP({"path": "/bbox", "queryStringParameters": {"url": "/local/tests/fixtures/rgb_cog.tif", "bbox":"-61.56544,16.22859,-61.563559,16.226925"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print(resp["body"]); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo

echo "/point"
python3.6 -c 'from tiler.api import APP; resp = APP({"path": "/point", "queryStringParameters": {"url": "/local/tests/fixtures/rgb_cog.tif", "coordinates":"-61.56463623161228,16.227860775481847"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print(resp["body"]); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo

echo "/metadata"
python3.6 -c 'from tiler.api import APP; resp = APP({"path": "/metadata", "queryStringParameters": {"url": "/local/tests/fixtures/rgb_cog.tif"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print(resp["body"]); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo

echo "/tilejson.json"
python3.6 -c 'from tiler.api import APP; resp = APP({"path": "/tilejson.json", "queryStringParameters": {"url": "/local/tests/fixtures/sar_cog.tif"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print(resp["body"]); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo

echo "Raster Tiles"
python3.6 -c 'from tiler.api import APP; resp = APP({"path": "/tiles/18/86242/119093.jpg", "queryStringParameters": {"url": "/local/tests/fixtures/rgb_cog.tif"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo

echo "Vector Tiles"
python3.6 -c 'from tiler.api import APP; resp = APP({"path": "/tiles/12/2161/2047.pbf", "queryStringParameters": {"url": "/local/tests/fixtures/lidar_cog.tif"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
python3.6 -c 'from tiler.api import APP; resp = APP({"path": "/tiles/12/2161/2047.pbf", "queryStringParameters": {"url": "/local/tests/fixtures/lidar_cog.tif", "feature_type": "polygon"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo

echo "Done"