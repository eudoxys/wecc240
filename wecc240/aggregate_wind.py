import os
import pandas as pd

file = f"{os.environ['HOME']}/Downloads/aggregate_node_wind_production.csv"
if os.path.exists(file):
    data = pd.read_csv(file,index_col=0,parse_dates=[0]).fillna(0).resample("1h").mean()/1000
    data.columns = [x.split("_")[0] for x in data.columns]
    data[sorted(data.columns)].round(3).to_csv("wecc240_2025_wind.csv",index=True,header=True)
else:
    print(f"You need to download {file} https://nrel-my.sharepoint.com/personal/rwhite_nrel_gov")
