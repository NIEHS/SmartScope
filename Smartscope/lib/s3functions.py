from storages.backends.s3boto3 import S3Boto3Storage
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)


class SmartscopeStorage(S3Boto3Storage):

    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    location = os.getenv('AWS_DATA_PREFIX')
    custom_domain = None

    def dir_exists(self, name):
        name = self._normalize_name(self._clean_name(name))
        # print(name)
        objs = self.connection.meta.client.list_objects(Bucket=self.bucket_name, Prefix=name, MaxKeys=1)
        if 'Contents' in objs:
            return True
        return False

    def download_temp(self, path):
        # name = self._normalize_name(self._clean_name(str(name)))
        logger.debug(path)
        name = path.name
        download_path = Path('/tmp', name)
        # with open(download_path, 'wb') as f:
        self.connection.meta.client.download_file(self.bucket_name, str(path), str(download_path))
        return download_path
