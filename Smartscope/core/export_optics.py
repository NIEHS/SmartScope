
import os
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoscreenViewer.settings')

# os.chdir(os.environ['SMARTSCOPE_DIR'])
# # os.environ['DJANGO_SETTINGS_MODULE'] = 'SmartscopeWorker.settings.settings'
# django.setup()
from Smartscope.core.models import *

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from random import random
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt


def maxOccurrences(my_list, key):
    return max([len([True for row in my_list if getattr(row, key) == val and getattr(row, key) is not None])
                for val in {getattr(x, key) for x in my_list}
                ])


def get_optic_groups(holes, hm):

    max_group = maxOccurrences(holes, 'bis_group')
    print(f'Splitting into {max_group} groups')

    for i, mic in enumerate(hm):
        if i == 0:
            array = np.array([mic.frames, mic.is_x, mic.is_y, 0])
            continue
        array = np.vstack((array, np.array([mic.frames, mic.is_x, mic.is_y, 0])))

    result = AgglomerativeClustering(n_clusters=max_group).fit(array[:, (1, 2)].astype(np.float64))

    array[:, 3] = result.labels_ + 1

    return array


def plot_optics_cluster(optics_array, directory=''):
    colors = {val: (random(), random(), random()) for val in set(optics_array[:, 3])}
    mydpi = 100
    fig = plt.figure(figsize=(512 / mydpi, 512 / mydpi), dpi=mydpi)
    ax = fig.add_subplot(111)
    ax.scatter(optics_array[:, 1].astype(float), optics_array[:, 2].astype(float), edgecolor='k', c=[colors[val] for val in optics_array[:, 3]])
    ax.set_xlabel('BIS x (\u03BCm)')
    ax.set_ylabel('BIS y (\u03BCm)')
    ax.set_aspect('equal')
    plt.savefig(os.path.join(directory, 'optic_groups.png'), bbox_inches='tight', dpi=mydpi)
    plt.close(fig='all')


class relion_star:
    relion_version = '# version 30001'

    def __init__(self, filepath, extension=None, directory='Micrographs'):
        self.filepath = filepath
        self.extension = extension
        self.directory = directory

    def optics_groups_header(self, migrographs, pixel_size, voltage, spherical_abberration, amplitude_contrast):
        scope_string = f'{pixel_size} {pixel_size} {voltage} {spherical_abberration} {amplitude_contrast}'
        string = f"""
{self.relion_version}

data_optics

loop_
_rlnOpticsGroupName #1
_rlnOpticsGroup #2
_rlnMicrographPixelSize #3
_rlnMicrographOriginalPixelSize #4
_rlnVoltage #5
_rlnSphericalAberration #6
_rlnAmplitudeContrast #7
"""
        for group in sorted(set(migrographs[:, 3])):
            string += f'opticsGroup{group} {group} {scope_string}\n'
        return string

    def optic_groups_mic(self, micrographs, mic_type):
        if mic_type == "micrograph":
            string = f"""
{self.relion_version}

data_micrographs

loop_
_rlnMicrographName #1
_rlnOpticsGroup #2
"""
        elif mic_type == "movie":
            string = f"""
{self.relion_version}

data_movies

loop_
_rlnMicrographMovieName #1
_rlnOpticsGroup #2
"""
        for (name, group) in micrographs[:, (0, 3)]:
            if self.extension is not None:
                name = '.'.join(name.split('.')[:-1]) + self.extension
            name = os.path.join(self.directory, name)
            string += ' '.join([name, group]) + '\n'
        return string

    def __enter__(self):
        self.file = open(self.filepath, 'w')
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()


def export_optics(grid_id, mic_directory, mic_extension, mic_type):
    holes = list(HoleModel.objects.all().filter(grid_id=grid_id, status='completed'))
    hm = list(HighMagModel.objects.all().filter(grid_id=grid_id, status='completed'))
    pixel_size = list(set([entry.pixel_size for entry in hm]))[0]
    grid = AutoloaderGrid.objects.get(grid_id=grid_id)
    session = grid.session_id
    print(session)
    scope = session.microscope_id

    os.chdir(grid.directory)
    print(os.getcwd())
    optics = get_optic_groups(holes, hm)
    plot_optics_cluster(optics)

    star = relion_star(f'{grid.name}.star', extension=mic_extension, directory=mic_directory)
    with star as f:
        f.write(star.optics_groups_header(optics, pixel_size, scope.voltage, scope.spherical_abberation, 0.1))
        f.write(star.optic_groups_mic(optics, mic_type))
