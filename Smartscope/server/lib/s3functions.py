import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import os
import json
import io


class SmartscopeStorage(S3Boto3Storage):

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = settings.AWS_DATA_PREFIX
    custom_domain = None

    def dir_exists(self, name):
        name = self._normalize_name(self._clean_name(name))
        # print(name)
        objs = self.connection.meta.client.list_objects(Bucket=self.bucket_name, Prefix=name, MaxKeys=1)
        if 'Contents' in objs:
            return True
        return False

    def download_temp(self, name):
        name = self._normalize_name(self._clean_name(name))
        # print(name)
        # bytes_buffer = io.BytesIO()
        with open('/tmp/tmp.mrc', 'wb') as f:
            self.connection.meta.client.download_fileobj(self.bucket_name, name, f)
        return '/tmp/tmp.mrc'
