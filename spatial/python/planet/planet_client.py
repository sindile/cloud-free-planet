from planet import api
from planet.api import filters
from geo_utils import GeoUtils
from pprint import pprint
from requests.auth import HTTPBasicAuth

import ssl
import requests
import time
import urllib.request
import shutil
import boto3
import concurrent

# PClientV1, class to simplify querying & downloading planet scenes using planet API V1
# We need to consider usage of a new API
class PClientV1():
    def __init__(self, api_key):
        self.api_key = api_key
        self.max_clouds = 0.25
        self.max_bad_pixels = 0.25
        self.maximgs = 1
        self.catalog_path = "catalog/"
        self.s3_catalog_bucket = "azavea-africa-test"
        self.s3_catalog_prefix = "planet/images"
        self.item_type = "PSScene4Band"
        self.asset_type = "analytic_sr"
        self.client = api.ClientV1(api_key = api_key)
        self.output_filename = "output.csv"
        self.output_encoding = "utf-8"
        self.s3client = boto3.client('s3')
        self.threads_number = 2
        self.executor = concurrent.futures.ThreadPoolExecutor(self.threads_number)
        self.downloads = []

    def await_downloads(self):
        for future_download in concurrent.futures.as_completed(self.downloads):
            print(future_download.result())

    # there are start_date and end_date present as it should be the part of a row retrieved from psql / tiff file
    def set_filters_sr(self, aoi, start_date='2017-12-15T00:00:00.000Z', end_date = '2018-03-15T00:00:00.000Z', id=''):
        # add an asset_filter for only those scenes that have an analytic_sr asset available
        date_filter = {
            'type': 'DateRangeFilter',
            'field_name': 'acquired',
            'config': {
                'gte': start_date,
                'lte': end_date
            }
        }

        cloud_filter = {
            'type': 'RangeFilter',
            'field_name': 'cloud_cover',
            'config': {
                'lte': self.max_clouds
            }
        }

        bad_pixel_filter = {
            'type': 'RangeFilter',
            'field_name': 'anomalous_pixels',
            'config': {
                'lte': self.max_bad_pixels
            }
        }

        location_filter = api.filters.geom_filter(aoi)

        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": aoi
        }

        asset_filter = {
            "type": "PermissionFilter",
            "config": ["assets.analytic_sr:download"]
        }

        string_filter = {
            "type": "StringInFilter",
            "field_name": "id",
            "config": [id]
        }

        filters_list = [date_filter, cloud_filter,geometry_filter, bad_pixel_filter, asset_filter]
        if (id != ''): 
            filters_list.append(string_filter)

        # combine filters:
        query = {
            'type': 'AndFilter',
            'config': filters_list
        }

        return query

    def request_intersecting_scenes(self, query):
        # build the request
        item_types = [self.item_type]  # params["lst_item_types"]
        request = api.filters.build_search_request(query, item_types)

        # post the request
        results = self.client.quick_search(request)
        return results

    # returns a full URI here
    def download_localfs(self, scene_id):
        output_file = "{}{}_{}.tif".format(self.catalog_path, scene_id, season)

        def sync(argz):
            # activation & download
            session = requests.Session()
            pprint(self.api_key)
            session.auth = (self.api_key, '')
            assets_uri = ("https://api.planet.com/data/v1/item-types/{}/items/{}/assets/").format(self.item_type, scene_id)
                
            assets_query_result = session.get(assets_uri)

            pprint(assets_query_result.status_code)
            item_activation_json = assets_query_result.json()
            # pprint(item_activation_json)
            item_activation_url = item_activation_json[self.asset_type]["_links"]["activate"]
            response = session.post(item_activation_url)
            print(response.status_code)
            while response.status_code!=204:
                time.sleep(30)
                response = session.post(item_activation_url)
                response.status_code = response.status_code
                print(response.status_code)

            item_url = 'https://api.planet.com/data/v1/item-types/{}/items/{}/assets'.format(self.item_type, scene_id)
            result = requests.get(item_url, auth = HTTPBasicAuth(self.api_key, ''))
            download_url = result.json()[self.asset_type]['location']

            # download
            with urllib.request.urlopen(download_url) as response, open(output_file, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

            return output_file

        self.downloads.append(self.executor.submit(sync, None))
        return output_file

    # TODO: lots of copy pasting happens there, abstract over it?
    # returns a full S3 URI here
    def download_s3(self, scene_id, season = ''):
        print("Downloading {}...".format(scene_id))
        output_key = "{}/{}_{}.tif".format(self.s3_catalog_prefix, scene_id, season)
        result = 's3://{}/{}'.format(self.s3_catalog_bucket, output_key)

        def sync(argz):
            # activation & download
            session = requests.Session()
            session.auth = (self.api_key, '')
            assets_uri = ("https://api.planet.com/data/v1/item-types/{}/items/{}/assets/").format(self.item_type, scene_id)
                
            assets_query_result = session.get(assets_uri)

            pprint(assets_query_result.status_code)
            item_activation_json = assets_query_result.json()
            # pprint(item_activation_json)
            item_activation_url = item_activation_json[self.asset_type]["_links"]["activate"]
            response = session.post(item_activation_url)
            print(response.status_code)
            while response.status_code!=204:
                time.sleep(30)
                response = session.post(item_activation_url)
                response.status_code = response.status_code
                print(response.status_code)

            item_url = 'https://api.planet.com/data/v1/item-types/{}/items/{}/assets'.format(self.item_type, scene_id)
            result = requests.get(item_url, auth = HTTPBasicAuth(self.api_key, ''))
            download_url = result.json()[self.asset_type]['location']

            # upload on s3 directly from the response
            with urllib.request.urlopen(download_url) as response:
                self.s3client.put_object(Body=response.read(), Bucket=self.s3_catalog_bucket, Key=output_key)

            return result

        self.downloads.append(self.executor.submit(sync, None))

        return result
