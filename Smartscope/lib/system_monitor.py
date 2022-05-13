import os


def disk_space(path):
    statvfs = os.statvfs(path)
    fs_size = statvfs.f_frsize * statvfs.f_blocks / 1e9
    fs_free = statvfs.f_frsize * statvfs.f_bavail / 1e9
    perc_full = round((1 - fs_free / fs_size) * 100, 2)
    return [round(fs_size, 1), round(fs_free, 1), perc_full]
