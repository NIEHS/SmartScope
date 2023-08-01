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
        name = self._normalize_name(name)
        objs = self.connection.meta.client.list_objects(
            Bucket=self.bucket_name, Prefix=name, MaxKeys=1)
        if 'Contents' in objs:
            return True
        return False

    def download_temp(self, path):
        name = path.name
        object_path = Path(self.location, path)
        download_path = Path(os.getenv('TEMPDIR'), name)
        if not download_path.exists():
            self.connection.meta.client.download_file(
                self.bucket_name,
                str(object_path),
                str(download_path)
            )
        return download_path

    def upload_file(self, file, path):
        object_path = Path(self.location, path)
        self.connection.meta.client.upload_file(
            file,
            self.bucket_name,
            str(object_path)
        )

