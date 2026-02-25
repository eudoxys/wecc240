"""Compute the aggregate net loads"""

import os
import warnings
import requests

import pandas as pd

from wecc240_2018 import wecc240_2018

pd.options.display.width = None
pd.options.display.max_columns = None
pd.options.display.max_rows = None

gis = pd.read_csv("gis/wecc240.csv",
    # index_col=["COUNTY","BUS_I"],
    converters={
        "COUNTY":str,
        "LOAD":float,
    })

# calculate county-level load contribution factors
county_loads = gis.groupby("COUNTY")["LOAD"].sum().to_frame()
county_loads = {x:y for x,y in county_loads.to_dict()["LOAD"].items() if x}
gis["LOAD_CF"] = [(y/county_loads[x] if x in county_loads and county_loads[x] > 0 else 0.0) for x,y in gis[["COUNTY","LOAD"]].values]

print(gis)

quit()

# def get_county_from_latlon(latitude, longitude):
#     """
#     Returns the county and state for a given latitude and longitude
#     using the U.S. Census Bureau Geocoder API.
#     """
#     url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
#    
#     params = {
#         "x": longitude,
#         "y": latitude,
#         "benchmark": "Public_AR_Current",
#         "vintage": "Current_Current",
#         "format": "json"
#     }
#    
#     response = requests.get(url, params=params)
#     response.raise_for_status()
#    
#     data = response.json()
#    
#     try:
#         county_info = data["result"]["geographies"]["Counties"][0]
#         county = county_info["COUNTY"]
#         state = county_info["STATE"]
#         return f"{state}{county}"
#     except (KeyError, IndexError):
#         return None
#
# found = {}
# for ndx,data in gis.iterrows():
#
#     if not data.GEOHASH in found:
#         county = get_county_from_latlon(data.LAT,data.LON)
#         found[data.GEOHASH] = county
#     else:
#         county = found[data.GEOHASH]
#     print(ndx,*data[["LAT","LON","GEOHASH","NAME","GEN","LOAD","BA"]].values,county,flush=True,sep=",")

dg = pd.read_csv("wecc240_2025_dg.csv",index_col=0,parse_dates=[0]).resample("1h").mean()/1000
total = pd.read_csv("wecc240_2025_total.csv",index_col=0,parse_dates=[0])

# print(total)
# print(-dg)

# identify nodes with DG but not listed in loads (shouldn't be any)
extra_dg_nodes = sorted(set(dg.columns) - set(total.columns))
assert not extra_dg_nodes, f"DG nodes not found in totals {sorted(v)}"

# identify nodes listed in totals but not found in DG list (need to be added to dg)
missing_dg_nodes = sorted(set(total.columns) - set(dg.columns))
if missing_dg_nodes:

    # create a "zero" dataframe to extend dg so net can be calculated for all load nodes
    no_dg = pd.DataFrame(
        data={x:[0.0]*len(dg) for x in missing_dg_nodes},
        index=dg.index,
        )
    dg = pd.concat([no_dg,dg],axis=1).fillna(0.0)

net = (total - dg)[sorted(total.columns)]

# identify nodes with DG but no load
energy = net.sum(axis=0).to_frame().fillna(0.0)
no_load = set(energy[energy<0].dropna().index)
print("DG nodes with no load",sorted(no_load))



# list of nodes that cannot have DG
# node_fixes = {
#     "9mtzm4":None, # MEXICO load outside US county dataset
#     "9mvffm":"9mvgw4", # IMPRLVLY -> IMPERIAL
#     "9q5zqv":"9qeh90", # MOJAVE -> LUGO
#     "9qe6tq":"9qd9xh", # HELMS -> GREGG
#     "9qhkxd":"9qeh90", # ADELANTO -> LUGO
#     "9qhsdk":"9qeh90", # VICTORVL -> LUGO
#     "9qndpr":"9mvgw4", # PARKER -> IMPERIAL
#     "9qq5wv":"9qqk6u", # ELDORADO -> MEAD
#     "9r0vxp":"9r1jcf", # OLINDA -> COTWDPGE
#     "9rg8bx":"9r9uxw", # BURNS -> SUMMER L
#     "9rpbwn":"9x06gc", # INTERMT -> MONA
#     "c21g7u":"c21g7y", # CELILOCA -> BIG EDDY
#     "c2c10y":None, # BC Hydro load outside US county dataset
#     "c2u6xt":None, # AESO load outside US county dataset
# }
#
# not_fixed = set(missing_dg_nodes) - set(node_fixes)
# if not_fixed != set():
#     warnings.warn(f"{not_fixed} are not fixed")
#
# for node,mapto in node_fixes.items():
#     if mapto is None:
#         print(node,"is outside USA")
#     else:
#         print("moving",node,"DG to",mapto)
#         # print(net[[mapto,node]])
#         # net.loc[:,mapto] = net.loc[:,mapto] + net.loc[:,node]
#         # net.drop(node,axis=1,inplace=True)

net.round(3).to_csv("wecc240_2025_net.csv",index=True,header=True)

