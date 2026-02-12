import os
import pandas as pd

dg = pd.read_csv("wecc240_2025_dg.csv",index_col=0,parse_dates=[0])
load = pd.read_csv("wecc240_2025_load.csv",index_col=0,parse_dates=[0])
net = load - dg

print(net)

net.round(3).to_csv("wecc240_2025_net.csv",index=True,header=True)
