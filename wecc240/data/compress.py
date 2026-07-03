"""Compress a CSV file for Pandas"""

import os
import sys
import pandas as pd

if len(sys.argv) < 2:
    print("Syntax: python3 compress.py [CSVFILE ...]",file=sys.stderr)
    sys.exit(1)

for csvname in sys.argv[1:]:

    df = pd.read_csv(csvname)
    df.to_csv(csvname+".gz",index=False,compression="gzip")
