import pandas as pd

DTFORMAT = "%Y-%m-%d %H:%M:%S%z"
# read GIS data
wecc240_gis = pd.read_csv("gis/wecc240.csv")

# read solar data
solar = pd.read_csv("data/aggregate_node_solar_production(in).csv",
    index_col="timestamp",
    parse_dates=["timestamp"],
    ).fillna(0)/1000
solar = solar.resample("1h").mean()[sorted(solar.columns)]
solar.columns = [x.replace("_solar","") for x in solar.columns]

# check solar data
invalid = set(solar.columns)-set(wecc240_gis.GEOHASH)
if invalid:
    raise Exception(f"invalid solar nodes {invalid}")
else:
    total = solar.sum(axis=1)
    peak = total.max()
    peak_dt = total.index[total==peak].tz_convert("US/Pacific").to_pydatetime()[0]
    print(f"Peak solar generation: {peak/1000:.1f} GW on {peak_dt.strftime(DTFORMAT)}")

wind = pd.read_csv("data/aggregate_node_wind_production(in).csv",
    index_col="timestamp",
    parse_dates=["timestamp"],
    ).fillna(0)/1000
wind = wind.resample("1h").mean()[sorted(wind.columns)]
wind.columns = [x.replace("_wind","") for x in wind.columns]

# check wind data
invalid = set(wind.columns)-set(wecc240_gis.GEOHASH)
if invalid:
    raise Exception(f"invalid wind nodes {invalid}")
else:
    total = wind.sum(axis=1)
    peak = total.max()
    peak_dt = total.index[total==peak].tz_convert("US/Pacific").to_pydatetime()[0]
    print(f"Peak wind generation: {peak/1000:.1f} GW on {peak_dt.strftime(DTFORMAT)}")

