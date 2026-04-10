"""Check solar, wind, and DG data to make sure they're in the correct format"""
import os
import re
import pandas as pd

for file in [x for x in os.listdir() if x.endswith(".csv.gz")]:
    print(f"{file}",end="...",flush=True)
    try:
        data = pd.read_csv(file,index_col=[0],parse_dates=[0]).resample("1h").mean().fillna(0.0).round(3)
        data.columns = [x.split("_")[0] for x in data.columns]
        data.to_csv(file,index=True,header=True,compression="gzip")
        print("ok")
    except Exception as err:
        print(err)