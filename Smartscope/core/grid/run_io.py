import os
from Smartscope.lib.image.montage import Montage
from Smartscope.lib.file_manipulations.file_manipulations import split_path, file_busy, copy_file

def get_file(file, remove=True):
    path = split_path(file)
    file_busy(path.file, path.root)
    return copy_file(path.path, remove=remove)


def get_file_and_process(raw, name, directory='', force_reprocess=False):
    if force_reprocess or not os.path.isfile(raw):
        path = os.path.join(directory, raw)
        get_file(path, remove=True)
    montage = Montage(name)
    montage.load_or_process(force_process=force_reprocess)
    return montage