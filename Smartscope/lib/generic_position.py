#!/usr/env/bin python


import os
import re
import time
from math import cos, sin, radians
from ast import literal_eval
import pandas as pd
import logging

proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')


class GenericPosition:

    def __init__(self):
        pass

    def pixel_to_specimen_coords(self, x, y):
        """Convert pixel coords to specimen coordinates"""
        angle = radians(self.metadata.RotationAngle.iloc[-1])
        if isinstance(x, int) or isinstance(x, float):
            rotated_x = (x * cos(angle) + y * sin(angle))
            rotated_y = (y * cos(angle) - x * sin(angle))
        elif isinstance(x, list):
            rotated_x = []
            rotated_y = []
            for i, j in zip(x, y):
                rotated_x.append(i * cos(angle) + j * sin(angle))
                rotated_y.append(j * cos(angle) - i * sin(angle))
        return rotated_x, rotated_y

    def parse_mdoc(self, file=None, movie=False):
        """
        Opens an mdoc file and returns a dataframe with the different values from the file
        """
        pattern = re.compile(r'(\w*)\s=\s([\-\w\.\s\\:]+)\n')

        if file is None:
            image = self.image
        else:
            image = file
        try:
            with open(f'{image}.mdoc', 'r') as file:
                mdocFile = file.read().split('\n\n')
        except FileNotFoundError:
            time.sleep(2)
            with open(f'{image}.mdoc', 'r') as file:
                mdocFile = file.read().split('\n\n')
                proclog.debug(mdocFile)
        if movie:
            stacks = [m for m in mdocFile[1:] if '[MontSection =' not in m]
        else:
            stacks = [m for m in mdocFile[3:] if '[MontSection =' not in m]
            # self.pixel_size = float(re.findall(pattern, mdocFile[0])[0][1])

        for stack in stacks:
            mdocValues = re.findall(pattern, '\n\n'.join([mdocFile[0], stack]))
            mdoc = pd.DataFrame()
            for key, val in mdocValues:
                try:
                    mdoc[key] = [[int(i) for i in val.split(' ')] if len(val.split(' ')) > 1 else int(val)]
                except:
                    try:
                        mdoc[key] = [[float(i) for i in val.split(' ')] if len(val.split(' ')) > 1 else float(val)]
                    except:
                        mdoc[key] = [val]
            if 'OperatingMode' in mdoc.keys() and mdoc.at[len(mdoc.index) - 1, 'OperatingMode'] == 2:
                mdoc.at[len(mdoc.index) - 1, 'Binning'] = mdoc.at[len(mdoc.index) - 1, 'Binning'] * 2
            if 'metadata' not in self.__dict__:
                self.metadata = mdoc
            else:
                self.metadata = pd.concat([self.metadata, mdoc], ignore_index=True, sort=False)

        self.pixel_size = self.metadata.PixelSpacing.iloc[-1]
        return self

    def save_metadata(self):
        self.metadata.to_pickle(self.metadataFile)
        if 'metadataIter' in self.__dict__:
            self.metadataIter.to_pickle(self.metadataIterFile)

    def read_metadata(self, iscsv=False, itermeta=True, fpath=None):
        if fpath is None:
            fpath = self.metadataFile

        def lit_eval(x):
            if isinstance(x, str):
                print(x)
                x = literal_eval(x)
            return x

        if iscsv:
            file = fpath.split('.')[0] + '.txt'
            self.metadata = pd.read_csv(file, sep='\t')
            self.metadata = fpath.applymap(lit_eval)

        if os.path.isfile(fpath):
            self.metadata = pd.read_pickle(fpath)
        if itermeta:
            if os.path.isfile(self.metadataIterFile):
                self.metadataIter = pd.read_pickle(self.metadataIterFile)
