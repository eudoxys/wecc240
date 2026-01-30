"""Aggregate county/country loads to network nodes

Usage
-----
    
    python3 aggregate_load.py [--debug] [--refresh] YEAR ...

Example
-------

To get the aggregate load data for 2020 run the command

    python2 aggregate_load.py 2020

which outputs the following

    /Users/david/GitHub/eudoxys/wecc240/wecc240/aggregate_load.py:62: PerformanceWarning: DataFrame is highly fragmented.  This is usually the result of calling `frame.insert` many times, which has poor performance.  Consider joining all columns at once using pd.concat(axis=1) instead. To get a de-fragmented frame, use `newframe = frame.copy()`
      result[node] = data.loc[result.index,"load_MW"]
    /Users/david/GitHub/eudoxys/wecc240/wecc240/aggregate_load.py:62: PerformanceWarning: DataFrame is highly fragmented.  This is usually the result of calling `frame.insert` many times, which has poor performance.  Consider joining all columns at once using pd.concat(axis=1) instead. To get a de-fragmented frame, use `newframe = frame.copy()`
      result[node] = data.loc[result.index,"load_MW"]
    WARNING:/Users/david/GitHub/eudoxys/wecc240/wecc240/aggregate_load.py:Mexico/9mtzm4.csv does not exist
    WECC load for 2020
    ------------------
    Peak demand......... 164.4 GW
    Peak day............ 2020-08-18 21:00:00 UTC
    Total consumption... 928.7 TWh
"""

if __name__ == "__main__":
    import os
    import datetime as dt
    import sys
    import pytz
    import logging

    import pandas as pd

    from loads.aggregate import aggregate

    pd.options.display.max_columns = None
    pd.options.display.width = None
    # pd.options.display.max_rows = None

    refresh = "--refresh" in sys.argv
    debug = "--debug" in sys.argv

    wecc240_gis = pd.read_csv("gis/wecc240.csv")
    canada = set(wecc240_gis[wecc240_gis.LAT>49].GEOHASH.values)
    mexico = set(wecc240_gis.set_index("GEOHASH").loc[["9mtzm4"]].index.values)
    omitted = canada|mexico

    locations,latlon = list(wecc240_gis.GEOHASH),list(zip(wecc240_gis.LAT,wecc240_gis.LON))
    targets = {x:latlon[locations.index(x)] for x in set(locations) if x not in omitted}

    try:
        year = int([x for x in sys.argv[1:] if not x.startswith("-")][1])
    except:
        print("Syntax: python3 aggregate.py [--debug] [--refresh] YEAR",file=sys.stderr)
        year = 2020
        print(f"Using default aggregates for {year=} with {debug=}",flush=True)

    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    _logger = logging.getLogger(__file__)

    result = aggregate(targets,year,"elec_net_MW",refresh=refresh)[0]

    for country,node in [("Canada",x) for x in canada] + [("Mexico",x) for x in mexico]:
        file = f"{country}/{node}.csv"
        print("Reading",file,end="...",flush=True)
        if os.path.exists(file):
            data = pd.read_csv(file,index_col=["timestamp"],parse_dates=["timestamp"])
            result[node] = data.loc[result.index,"load_MW"]
            print(data)
            print(f"ok ({data.load_MW.sum()/1e3:.1f} GWh)")
        else:
            _logger.warning(f"{file} does not exist")

    total = result[24:].sum(axis=1)
    print(f"WECC load for {year}")
    print("------------------")
    print(f"Peak demand......... {total.max()/1000:.1f} GW")
    peak_dt = total[total==total.max()].index.to_pydatetime()[0]
    print(f"Peak day............ {peak_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Total consumption... {total.sum()/1e6:.1f} TWh")

    result[sorted(result.columns)].to_csv("wecc240_2020_load.csv",index=True,header=True)
