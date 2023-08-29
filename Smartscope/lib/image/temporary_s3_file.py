from typing import List
from pathlib import Path
import logging

from .smartscope_storage import SmartscopeStorage

logger = logging.getLogger(__name__)


def get_S3_path(working_dir, file):
    return Path(working_dir, file)


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
