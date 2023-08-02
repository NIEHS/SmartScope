'''
'''
import re
import pandas as pd
import logging
import mrcfile

logger = logging.getLogger(__name__)


def parse_mdoc(mdocFile: str, movie: bool = False) -> pd.DataFrame:
    """
    Opens an mdoc file and returns a dataframe 
    with the different values from the file and the pixel size
    """
    pattern = re.compile(r'(\w*)\s=\s([\-\w\.\s\\:]+)\n')
    metadata= None
    with open(mdocFile, 'r') as file:
        mdocFile = file.read().split('\n\n')

    if movie:
        stacks = [m for m in mdocFile[1:] if '[MontSection =' not in m]
    else:
        stacks = [m for m in mdocFile[3:] if '[MontSection =' not in m]

    for index, stack in enumerate(stacks):
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

        if index == 0:
            metadata = mdoc
        else:
            metadata = pd.concat([metadata, mdoc], ignore_index=True, sort=False)

    return metadata


def save_mrc(file, image, apix, start_values, overwrite=True):
    '''
    save image into a file in mrc format
    '''
    with mrcfile.new(file, overwrite=overwrite) as mrc:
        mrc.set_data(image)
        header = mrc.header
        header.nxstart = start_values[1]
        header.nystart = start_values[0]
        header.cella = (apix * header.nx, apix * header.ny, apix * header.nz)
        header.mx = header.nx
        header.my = header.ny