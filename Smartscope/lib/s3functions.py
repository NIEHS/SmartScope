from typing import List
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
        name = path.name
        object_path = Path(self.location, path)
        download_path = Path(os.getenv('TEMPDIR'), name)
        if not download_path.exists():
            self.connection.meta.client.download_file(self.bucket_name, str(object_path), str(download_path))
        return download_path


class TemporaryS3File:

    def __init__(self, files: List) -> None:
        self.files = files
        self.temporary_files = []

    def __enter__(self):
        self.download_temporary_files_from_s3()
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self.remove_temporary_files()

    def download_temporary_files_from_s3(self) -> None:
        storage = SmartscopeStorage()
        for file in self.files:
            self.temporary_files.append(storage.download_temp(file))

    def remove_temporary_files(self) -> None:
        logger.debug(f'Removing temprary files {self.temporary_files}')
        [file.unlink() for file in self.temporary_files]
