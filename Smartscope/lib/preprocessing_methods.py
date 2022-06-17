from typing import List
import pandas as pd
from pathlib import Path


def get_CTFFIN4_data(path: Path) -> List[float]:
    with open(path, 'r') as f:
        lines = [[float(j) for j in i.split(' ')] for i in f.readlines() if '#' not in i]

        ctf = pd.DataFrame.from_records(lines, columns=['l', 'df1', 'df2', 'angast', 'phshift', 'cc', 'ctffit'], exclude=[
            'l', 'phshift'])

        return dict(defocus=(ctf.df1 + ctf.df2) / 2,
                    astig=ctf.df1 - ctf.df2,
                    angast=ctf.angast,
                    ctffit=ctf.ctffit)
