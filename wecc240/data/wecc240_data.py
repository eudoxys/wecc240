"""WECC240 model data accessors

Progress Callbacks
------------------

Long-running functions support a progress callback function as follows:

- `progress`: callback for slow loops
  - `event`: `"processing"` or `"exception"`
  - `data`: data associated with the event
    - Processing data:
      - `states`: state being processed
      - `county`: county being processed
    - Exception data:
      - `type`: exception type
      - `value`: exception value
      - `trace`: exception traceback

Precision
---------

The `precision` argument used by many `read_*` calls is only effective when
creating or refreshing the data file.
"""

import os
import sys
import datetime as dt
from warnings import warn
from typing import Callable

import numpy as np
import pandas as pd
import cvxpy as cp

from fips import Counties
from loads import Total
from eia import HS861m, Form923, Form861m
from geohash import nearest2

PRECISION=4
"""Default precision for data files"""

#
# Set date ranges for hour, months, and years
#
start_dt = "2018-01-01 00:00:00+0000"
"""Start date for data"""

end_dt = "2022-12-31 23:59:59+0000"
"""Stop date for data"""

hour_range,month_range,year_range = [
    pd.date_range(start=start_dt,end=end_dt,freq=x) 
    for x in ["1h","MS","YS"]
    ]
"""Hour, month, and year date ranges to use in data frames"""

#
# Read counties and states to be processed (counties, states)
# 
def read_counties(*,refresh:bool|str=False) -> pd.DataFrame:
    """Read counties in WECC

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `ST`: state abbreviation
      - `COUNTY`: county name
      - `RO`: reliability organization
      - `FIPS`: county FIPS code
      - `LAT`: county centroid latitude
      - `LON`: county centroid longitude
      - `GEOHASH`: county centroid geohash
      - `TZOFFSET`: county timezone offset from UTC (east is positive)
      - `DST`: daylight savings time flag (0 no DST, 1 DST is in use)
      - `SYSTEM`: interconnection in which county is located
      - `REGION`: operating region in which county is located
      - `COUNTY_ST`: county/state name used by data frame columns
    """
    if os.path.exists("counties.csv") and not refresh:
        counties = pd.read_csv("counties.csv",
            index_col=[0,1],
            converters=({"FIPS":str})
            )
    else:
        counties = Counties(
            use_index="RO",
            selection="WECC",
            set_index=["ST","COUNTY"],
            )
        counties["COUNTY_ST"] = [f"{y} {x}" for x,y in counties.index]
        counties.to_csv("counties.csv",index=True)
    return counties.reset_index()

def read_states(*,refresh:bool|str=False) -> list:
    """Read list of states

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    Returns
    -------
    - `list`: list of states
    """
    states = read_counties(refresh=refresh=='all').ST.unique().tolist()
    return states

#
# Read network GIS data (bus_gis)
#
def read_bus_gis(*,refresh:bool|str=False) -> pd.DataFrame:
    """Read bus gis data

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `BUS_I`: bus id
      - `GEOHASH`: bus geohash
      - `LAT`: bus latitude
      - `LON`: bus longitude
      - `NAME`: bus name
      - `GEN`: bus generation (MW, `NaN` for PQ busses)
      - `LOAD`: bus load (MW)
      - `BA`: bus balancing authority
      - `FIPS`: bus county FIPS code
    """
    if os.path.exists("bus_gis.csv") and not refresh:
        bus_gis = pd.read_csv("bus_gis.csv",
            index_col=[0,1],
            converters={"FIPS":str}
            )
    else:
        bus_gis = pd.read_csv("../gis/wecc240.csv",
            index_col=["BUS_I","GEOHASH"],
            converters={"COUNTY":str},
            ).rename({"COUNTY":"FIPS"},axis=1)
        bus_gis.to_csv("bus_gis.csv",index=True)
    return bus_gis.reset_index()

#
# Read read load bus list (load_bus)
#
def read_bustype(
    bustype='load',
    *,
    country=None,
    refresh:bool|str=False,
    ) -> pd.DataFrame:
    """Read bus type data

    Arguments
    ---------

    - `bustype`: bus type to read (`"load"` default, `"node"`, `"gen"`, `None`
      for any bustype)

    - `country`: country in which bus is located (`"US"` or `"CA"`, `None` for
      any country)

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file (see `read_bus_gis`)

    Description
    -----------

    The following criteria are used to select busses:

    - `bustype=='load' --> LOAD > 0`

    - `bustype=='node' --> LOAD == 0`

    - `bustype=='gen' --> ~GEN.isnull()`
    """
    bus_gis = read_bus_gis(refresh=refresh)
    filename = f"bustype_{bustype}_{country}.csv"
    if os.path.exists(filename):
        bus_gis = pd.read_csv(filename)
    else:
        if country == "US":
            bus_gis = bus_gis[bus_gis["FIPS"]!=""]
        elif country == "CA":
            bus_gis = bus_gis[bus_gis["FIPS"]==""]
        elif country is not None:
            raise ValueError(f"{country=} is not valid")
        if bustype == "load":
            bus_gis = bus_gis[bus_gis["LOAD"]>0]
        elif bustype == "node":
            bus_gis = bus_gis[bus_gis["LOAD"]==0]
        elif bustype == "gen":
            bus_gis = bus_gis[~bus_gis["GEN"].isnull()]
        elif bustype is not None:
            raise ValueError(f"{bustype=} not valid")
        bus_gis.to_csv(filename,index=False)
    return bus_gis

#
# Read node DG from NLR (node_dg)
#
def read_node_dg(*,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ) -> pd.DataFrame:
    """Read node DG data

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - `...`: node geohash power (MW)
    """

    # copied from NLR aggregated solar dg data -> manually refreshed
    if refresh:
        warn("node_dg.csv.gz must be manually refreshed from NLR data repository")

    node_dg = pd.read_csv("node_dg.csv.gz",
        index_col=[0],
        parse_dates=[0],
        ).resample("1h").mean() / 1e3 # convert from kW to MW
    
    # remove "_dist_solar" from columns names
    node_dg.columns = [x.split("_")[0] for x in node_dg.columns] 

    # check for missing nodes
    load_nodes = set(read_bustype("load",country="US")["GEOHASH"])
    dg_nodes = set(node_dg.columns)
    noload = sorted(dg_nodes - load_nodes)
    if noload:
        warn(f"DG provided on the following nodes with zero loads: {', '.join(noload)}")
    nodg = sorted(load_nodes - dg_nodes)
    if nodg:
        warn(f"DG not provided on the following nodes with non-zero loads: {', '.join(nodg)}")

    return node_dg.sort_index().round(precision).reset_index()

#
# Read state gen, load, and dg monthly energy (state_mwh)
#
def read_state_mwh(*,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ) -> pd.DataFrame:
    """Read state monthly energy use

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - `gen`: total generation energy (TWh)
      - `load`: total load energy (TWh)
      - `dg`: total distributed generation energy (TWh)
    """
    if os.path.exists("state_mwh.csv") and not refresh:
        state_mwh = pd.read_csv("state_mwh.csv",index_col=[0],parse_dates=[0])
    else:
        
        states = read_states()

        # Read Form923 (gen)
        gen = []
        for date in year_range:
            gen.append(Form923(date.year,states=states))
        gen = pd.concat(gen).groupby(["timestamp","state"]).sum().rename({"gen_mwh":"gen"},axis=1).round(3)

        # Read HS861m (load)
        load = []
        for _year in range(2018, 2023):
            for _month in range(1, 13):
                _df = HS861m(_year, _month)[["tot_energy_mwh"]].reset_index()
                _df = _df[_df["state"].isin(states)]
                _df["timestamp"] = dt.datetime.strptime(
                    f"{_year}-{_month}-1 00:00:00+0000", "%Y-%m-%d %H:%M:%S%z"
                )
                load.append(_df)
        load = (
            pd.concat(load)
            .set_index(["timestamp", "state"])
            .rename({"tot_energy_mwh": "load"}, axis=1)
            .sort_index()
        )

        # Read Form 861m (dg)
        dg = []
        for _year in range(2018,2023):
            for _month in range(1,13):
                _df = Form861m(_year,_month)[["date","state","tot_mwh"]].rename({"date":"timestamp"},axis=1)
                dg.append(_df[_df["state"].isin(states)])
        dg = pd.concat(dg).set_index(["timestamp","state"]).rename({"tot_mwh":"dg"},axis=1).sort_index()
       
        state_mwh = pd.concat([gen, load, dg], axis=1).fillna(0).round(precision)
        state_mwh.to_csv("state_mwh.csv")
    return state_mwh.reset_index()

#
# Read county total not including DG (county_total)
#
def read_county_total(*,
    refresh:bool|str=False,
    progress:Callable=lambda *args,**kwargs:None,
    precision:int=PRECISION,
    ) -> pd.DataFrame:
    """Read county total hourly power demand (not including DG)

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `progress`: progress callback function

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: county/state name total power (MW)
    """
    filename = "county_total.csv.gz"
    if os.path.exists(filename) and not refresh:
        county_total = pd.read_csv(filename,index_col=[0],parse_dates=[0])
    else:
        counties = read_counties(refresh=refresh=='all')
        county_total = pd.DataFrame(
            data={x:[float('nan')]*len(hour_range) for x in counties["COUNTY_ST"]},
            index=hour_range,
            )
        Total.cache = None # disable Total result caching (limit memory use)
        print(counties)
        for state,county in counties[["ST","COUNTY"]].values:
            progress(event="processing",data={"county":county,"state":state})
            retry = 5
            while retry > 0:
                try:
                    data = Total(state,county,date_range=hour_range,samples=0)
                    break
                except Exception as err:
                    retry -= 1
                    exc = err
                    e_type,e_value,e_trace = sys.exc_info()
                    progress(
                        event="exception",
                        data={
                            "type":e_type,
                            "value": e_value,
                            "trace": e_trace,
                            },
                        )
            if retry == 0:
                raise exc
            nz = data[data["elec_total_MW"]>0].index
            county_total.loc[nz,f"{county} {state}"] = data.loc[nz,"elec_total_MW"]
        county_total.rename_axis("timestamp",inplace=True)
        county_total = county_total.round(precision)
        county_total.to_csv(filename,index=True,compression="gzip")
    return county_total.copy().reset_index()

#
# Read county-node mapping
#
def read_county_node_map(*,
    refresh:bool|str=False,
    ) -> pd.DataFrame:
    """Read county-to-node mapping

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    Returns
    -------
    - `pandas.DataFrame`: mapping of county/state name to node geohash
      - `county_st`: county/state name
      - `gen`: nearest generation node
      - `load`: nearest load node
      - `any`: nearest node of any bustype
    """
    if os.path.exists("county_node_map.csv") and not refresh:
        return pd.read_csv("county_node_map.csv")
    else:
        counties = read_counties(refresh=refresh=='all')
        gen_bus = bus_bustype("gen")
        load_bus = bus_bustype("load")
        county_node_map = {"gen":{},"load":{},"any":{}}
        for _bustype,_buslist in {"gen":gen_bus,"load":load_bus,"any":bus_gis}.items():
            bus_latlon = _buslist.set_index("GEOHASH")[["LAT","LON"]].round(6)
            node_latlon = bus_latlon[~bus_latlon.duplicated()].reset_index().values.tolist()
            county_latlon = counties[["COUNTY_ST","LAT","LON"]].values.tolist()
            for _county,_lat,_lon in county_latlon:
                county_node_map[_bustype][_county] = node_latlon[nearest2((_lat,_lon),[(x,y) for _,x,y in node_latlon])[0]][0]
                if _county == "San Diego CA":
                    print(_county,'-->',county_node_map[_bustype][_county])
        county_node_map = pd.DataFrame(county_node_map).rename_axis("county_st")
        county_node_map["county"] = [" ".join(x.split()[:-1]) for x in county_node_map.index]
        county_node_map["st"] = [x.split()[-1] for x in county_node_map.index]
        county_node_map.sort_values(["st","county"],inplace=True)

        county_node_map = county_node_map[["gen","load","any"]].reset_index()
        county_node_map.to_csv("county_node_map.csv",index=False,header=True)
    return county_node_map



#
# Read node total load not including DG (node_total)
#
def read_node_total(*,
    refresh:bool|str=False,
    progress:Callable=lambda *args,**kwargs:None,
    precision:int=PRECISION,
    ) -> pd.DataFrame:
    """Read node total hourly power demand (not including DG)

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `progress`: progress callback function

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: node name total power (MW)
    """
    filename = "node_total.csv"
    if os.path.exists(filename) and not refresh:
        node_total = pd.read_csv(filename,parse_dates=[0])
    else:
        county_node_map = read_county_node_map(refresh=refresh=='all')\
            .set_index("county_st")
        county_total = read_county_total(refresh=refresh=='all').set_index("timestamp")
        node_total = pd.DataFrame(
            data={x:[0]*len(county_total.index) for x in county_node_map["load"]},
            index=county_total.index,
            ).rename_axis("timestamp")
        for county_st in county_total.columns:
            state,county = county_st.split()[-1]," ".join(county_st.split()[:-1])
            progress(event="processing",data={"state":state,"county":county})
            node = county_node_map.loc[county_st]["load"]
            total = county_total[county_st].fillna(0)
            node_total[node] += total
        node_total = node_total[sorted(node_total.columns)].replace(0,np.nan).round(precision)

        node_total.reset_index(inplace=True)
        node_total.to_csv(filename,index=False,header=True)

    return node_total

#
# Read county-to-node contribution factors (county_node_cf)
#
def read_county_node_cf(*,
    refresh:bool|str=False,
    progress:Callable=lambda *args,**kwargs:None,
    precision:int=PRECISION+1,
    ) -> pd.DataFrame:
    """Read county-to-node contribution factors

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `progress`: progress callback function

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: county name contribution factor (per unit)
    """
    filename = "county_node_cf.csv.gz"
    if os.path.exists(filename) and not refresh:
        county_node_cf = pd.read_csv(filename,parse_dates=[0])
    else:
        node_total = read_node_total(refresh=refresh=="all").set_index("timestamp")
        # no need to refresh all again
        county_node_map = read_county_node_map(refresh=False)\
            .set_index("county_st")
        county_node_cf = read_county_total(refresh=False).set_index("timestamp")
        for county_st in county_node_cf.columns:
            state,county = county_st.split()[-1]," ".join(county_st.split()[:-1])
            progress(event="processing",data={"state":state,"county":county})
            node = county_node_map.loc[county_st]["load"]
            total = node_total[node]
            nz = total[total!=0].index
            county_node_cf.loc[nz,county_st] /= total.loc[nz]
        county_node_cf = county_node_cf.round(precision).reset_index()
        county_node_cf.to_csv(filename,index=False,header=True,compression="gzip")
    return county_node_cf

#
# Read county distribute generation (county_dg)
#
def read_county_dg(*,
    refresh:bool|str=False,
    progress:Callable=lambda *args,**kwargs:None,
    precision:int=PRECISION,
    ):
    """Read county distributed generation power

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `progress`: progress callback function

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: county name distributed generation (MW)
    """
    filename = "county_dg.csv"
    if os.path.exists(filename) and not refresh:
        county_dg = pd.read_csv(filename,parse_dates=[0])
    else:
        node_dg = read_node_dg(refresh=refresh=="all").set_index("timestamp")
        # no need to refresh all again
        county_node_map = read_county_node_map(refresh=False)\
            .set_index("county_st")
        county_dg = read_county_node_cf(refresh=False).set_index("timestamp")
        for county_st in county_dg.columns:
            state,county = county_st.split()[-1]," ".join(county_st.split()[:-1])
            progress(event="processing",data={"state":state,"county":county})
            node = county_node_map.loc[county_st]["load"]
            try:
                county_dg.loc[:,county_st] *= node_dg[node]
            except KeyError as err:
                county_dg.loc[:,county_st] = 0
        county_dg = county_dg.copy().round(precision).reset_index()
        county_dg.to_csv(filename,index=False,header=True)
    return county_dg

#
# Read county net load (county_net)
#
def read_county_net(*,
    refresh:bool|str=False,
    progress:callable=lambda *args,**kwargs:None,
    precision:int=PRECISION
    ):
    """Read the county net load

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `progress`: progress callback function

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: county name net load (MW)
    """
    if os.path.exists("county_net.csv") and not refresh:
        county_net = pd.read_csv("county_net.csv",parse_dates=[0])
    else:
        county_total = read_county_total(refresh=refresh=="all").set_index("timestamp")
        county_dg = read_county_dg(refresh=refresh=="all").set_index("timestamp")
        county_net = ( county_total - county_dg ).round(precision).reset_index()
        county_net.to_csv("county_net.csv",index=False,header=True)

    return county_net

#
# Read node net load (node_net)
#
def read_node_net(*,
    refresh:bool|str=False,
    progress:callable=lambda *args,**kwargs:None,
    precision:int=PRECISION
    ):
    """Read the node net load

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `progress`: progress callback function

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: node name net load (MW)
    """
    if os.path.exists("node_net.csv") and not refresh:
        node_net = pd.read_csv("node_net.csv",parse_dates=[0])
    else:
        node_net = read_node_total(refresh=refresh=="all",precision=precision).set_index("timestamp")
        node_dg = read_node_dg(refresh=refresh=="all",precision=precision).set_index("timestamp")

        # node_net -= node_dg
        # node_net = node_net.round(precision).reset_index()
        # node_net.to_csv("node_net.csv",index=False,header=True)

        common = sorted(set(node_net.columns) & set(node_dg.columns))
        node_net.loc[:,common] -= node_dg.loc[:,common]
        node_net = node_net.round(precision).reset_index()
        node_net.to_csv("node_net.csv",index=False,header=True)

        # bus_gis = read_bus_gis().set_index("GEOHASH")
        # missing = set(bus_gis.loc[sorted(set(node_dg.columns) - set(common)),"NAME"].values.tolist())
        # print(sorted(set(node_dg.columns) - set(common)))
        # if missing:
        #     warn(f"DG found for non-existent loads: {', '.join(sorted(missing))}")

    return node_net

#
# Read state total (state_total)
#
def read_state_total(*,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ):
    """Read the state total power

    Arguments
    ---------

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: state abbreviation total energy (MWh)
    """

    filename = "state_total.csv"
    if os.path.exists(filename) and not refresh:
        state_total = pd.read_csv(filename,parse_dates=[0])
    else:
        states = read_states(refresh=refresh=="all")
        county_total = read_county_total(refresh=refresh=="all")\
            .set_index("timestamp")
        state_total = pd.DataFrame(
            data={x:[0]*len(county_total.index) for x in states},
            index=county_total.index,
            )
        for county_st in county_total.columns:
            state = county_st.split()[-1]
            state_total[state] += county_total[county_st]
        state_total = state_total.round(precision).reset_index()
        state_total.to_csv(filename,index=False,header=True)

    return state_total

#
# Read state dg (state_dg)
#
def read_state_dg(*,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ):
    """Read the state dg power

    Arguments
    ---------

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: state abbreviation dg energy (MWh)
    """

    filename = "state_dg.csv"
    if os.path.exists(filename) and not refresh:
        state_dg = pd.read_csv(filename,parse_dates=[0])
    else:
        states = read_states(refresh=refresh=="all")
        county_dg = read_county_dg(refresh=refresh=="all")\
            .set_index("timestamp")
        state_dg = pd.DataFrame(
            data={x:[0]*len(county_dg.index) for x in states},
            index=county_dg.index,
            )
        for county_st in county_dg.columns:
            state = county_st.split()[-1]
            state_dg[state] += county_dg[county_st]
        state_dg = state_dg.round(precision).reset_index()
        state_dg.to_csv(filename,index=False,header=True)
    return state_dg


#
# Read state net load (state_net)
#
def read_state_net(*,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ):
    """Read state net load

    Arguments
    ---------

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------

    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: state abbreviation net energy (MWh)
    """
    filename = "state_net.csv"
    if os.path.exists(filename) and not refresh:
        state_net = pd.read_csv(filename,parse_dates=[0])
    else:
        state_total = read_state_total(refresh=refresh=="all")\
            .set_index("timestamp")
        state_dg = read_state_dg(refresh=refresh=="all")\
            .set_index("timestamp")
        state_net = ( state_total - state_dg ).round(precision).reset_index()
        state_net.to_csv(filename,index=False,header=True)
    return state_net

#
# Read state energy calibration scalar (state_scalar)
#
def read_state_calibration(*,
    refresh:bool|str=False,
    precision:int=PRECISION+1,
    ):
    """Read state energy calibration scalar

    Arguments
    ---------

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: state abbreviation energy scalar (MWh)
    """
    if os.path.exists("state_calibration.csv") and not refresh:
        state_calibration = pd.read_csv("state_calibration.csv",parse_dates=[0])
    else:
        state_mwh = read_state_mwh(refresh=refresh=="all")\
            .set_index(["timestamp","state"])["load"]\
            .unstack(level="state")

        state_total = read_state_net(refresh=refresh=="all")\
            .set_index("timestamp")\
            .resample("MS")\
            .sum()
        
        state_calibration = ( state_total / state_mwh )\
            .round(precision)\
            .reset_index()
        state_calibration.to_csv("state_calibration.csv",index=False,header=True)

    return state_calibration

#
# Read node power rescale (node_scaled)
#
def read_node_project(
    projection:float|list[float],
    *,
    nodes:list[str]=None,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ):
    """Read node power projection

    Arguments
    ---------

    - `projection`: projection function(s)
      - `float`: simple scalar applied to all nodes
      - `list[float]`: polynomial (descending order) applied to all nodes

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: node geohash power rescaled (MW)

    Examples
    --------

    Scale everything by 1.1:

        read_node_project(1.1)

    Apply linear function `1.1 x + 1000` to all nodes

        read_node_project([1.1,1000])
        
    Apply linear function `1.1 x + 1000` to only CAISO nodes

        bus_gis = read_bus_gis().set_index("BA")
        caiso = set(bus_gis.loc["CA","GEOHASH"])
        read_node_project([1.1,1000],nodes=caiso)
    """
    if refresh is True:
        warn("read_node_project has no cached values to refresh")

    node_project = read_node_total(refresh=refresh=="all").set_index("timestamp")
    
    if nodes is None:
        nodes = node_project.columns
    elif set(nodes) != set(node_project.columns):
        warn(f"nodes {set(nodes) - set(node_project.columns)} are not found and ignored")
        nodes = [x for x in nodes if x in node_project.columns]

    if isinstance(projection,(int,float)): 

        # simple scalar
        node_project.loc[:,nodes] *= projection

    elif isinstance(projection,list) and all(isinstance(x,(int,float)) for x in projection):
        
        # polynomial function
        node_project.loc[:,nodes] = pd.DataFrame(
            data=np.polyval(projection,node_project.loc[:,nodes]),
            index=node_project.index,
            columns=nodes,
            )

    else:

        raise ValueError(f"{projection=} is not valid")

    return node_project.round(precision).reset_index()

#
# Read node power offset (node_offset)
#
def read_node_offset(
    date_range:pd.DatetimeIndex,
    peak:float,
    *,
    nodes:list[str]=None,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ) -> float:
    """Read node power offset

    Arguments
    ---------

    - `date_range`: date range over which to measure peak

    - `peak`: the desired peak (MW)

    - `nodes`: list of nodes to adjust (`None` is all nodes)

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: node geohash power offset (MWh)
    """
    if refresh is True:
        warn("read_node_project has no cached values to refresh")

    node_offset = read_node_net(refresh=refresh=="all").set_index("timestamp")
    
    if nodes is None:
        nodes = node_offset.columns
    elif set(nodes) != set(node_offset.columns):
        warn(f"nodes {set(nodes) - set(node_offset.columns)} are not found and ignored")
        nodes = [x for x in nodes if x in node_offset.columns]

    assert isinstance(peak,(int,float)), f"type of {peak=} is invalid"

    old = node_offset.loc[:,nodes].sum(axis=1).max()

    return peak - old

def read_node_calibration(
    *,
    refresh:bool|str=False,
    precision:int=PRECISION
    ):
    """Read node power calibration

    Arguments
    ---------

    - `date_range`: date range over which to measure peak

    - `energy`: 

    - `peak`: the desired peak (MW)

    - `nodes`: list of nodes to adjust (`None` is all nodes)

    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: date/time of record
      - ...: node geohash power calibration (MWh)
    """

    node_calibration = read_node_total(refresh=refresh=="all").set_index("timestamp")

    return node_calibration

#
# EIA-930 balancing authority load disaggregation (ba_load, county_ba,
# county_node_factor, county_ba_load, node_ba_load)
#
LOADS_COMMIT = "9341b1342fb64d23db0e169017fee6fa11821e46"
"""`eudoxys/loads` commit from which the BA disaggregation inputs are read"""

LOADS_URL = f"https://raw.githubusercontent.com/eudoxys/loads/{LOADS_COMMIT}/loads/"
"""URL of the `eudoxys/loads` package folder at `LOADS_COMMIT`"""

def read_ba_load(*,
    refresh:bool|str=False,
    ) -> pd.DataFrame:
    """Read EIA-930 balancing authority hourly demand

    Arguments
    ---------
    - `refresh`: force refresh of data file from `eudoxys/loads`

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: UTC date/time of the beginning of the hour
      - ...: EIA-930 BA code demand (MW)

    Description
    -----------
    The source is the cleaned EIA-930 "Demand (MW) (Adjusted)" series of the
    28 US Western Interconnection BAs that report demand, from
    `loads/_test/data/WECC_BA_hourly_load_2018-2022.csv` in `eudoxys/loads`
    (see that folder's `README.md` for the cleaning and gap filling). The
    source is UTC hour-ending; it is converted to UTC hour-beginning and
    reindexed to `hour_range`, so the first 8 hours of 2018 are `NaN`.
    BC Hydro, AESO and CFE report no demand to EIA-930 and are not included.
    """
    filename = "ba_load.csv.gz"
    if os.path.exists(filename) and not refresh:
        ba_load = pd.read_csv(filename,index_col=[0],parse_dates=[0])
    else:
        ba_load = pd.read_csv(LOADS_URL+"_test/data/WECC_BA_hourly_load_2018-2022.csv")
        ba_load.index = pd.DatetimeIndex(
            pd.to_datetime(ba_load["utc_hour_ending"],utc=True) - pd.Timedelta(hours=1),
            name="timestamp",
            )
        ba_load = ba_load.drop(["utc_hour_ending","pst_hour_ending"],axis=1)
        ba_load = ba_load.reindex(hour_range).rename_axis("timestamp")
        ba_load.to_csv(filename,index=True,header=True,compression="gzip")
    return ba_load.reset_index()

def read_county_ba(*,
    refresh:bool|str=False,
    ) -> pd.DataFrame:
    """Read county balancing authority participation factors

    Arguments
    ---------
    - `refresh`: force refresh of data file from `eudoxys/loads`

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `county_st`: county/state name
      - `ba`: EIA BA code
      - `factor`: fraction of the county's load served by the BA (the
        factors of a county sum to 1)
      - `method`: `eia861` (fitted to EIA-861 2018 utility sales),
        `override` (manual correction), or `state` (state BA shares)

    Description
    -----------
    Copied from `loads/wecc/county_ba.csv` in `eudoxys/loads`, which is built
    by `loads/wecc/county_ba.py` from the EIA-861 2018 service territory and
    retail sales data. BA codes not in EIA-930 (e.g., `SWPP`) can appear for
    border counties.
    """
    filename = "county_ba.csv"
    if os.path.exists(filename) and not refresh:
        county_ba = pd.read_csv(filename)
    else:
        county_ba = pd.read_csv(LOADS_URL+"wecc/county_ba.csv")
        county_ba.to_csv(filename,index=False,header=True)
    return county_ba

def read_county_node_factor(*,
    refresh:bool|str=False,
    ) -> pd.DataFrame:
    """Read county-to-node allocation factors

    Arguments
    ---------
    - `refresh`: force refresh of data file from `eudoxys/loads`

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `county_st`: county/state name
      - `node`: node geohash
      - `factor`: fraction of the county's load allocated to the node (the
        factors of a county sum to 1)
      - `method`: `bus` (county split among its in-county load busses in
        proportion to their load in the WECC 240 case) or `nearest` (county
        allocated entirely to its nearest load node in `county_node_map.csv`)

    Description
    -----------
    Copied from `loads/wecc/node_estimate_cf.csv` in `eudoxys/loads` (built
    by `loads/wecc/node_estimate.py`), with column `cf` renamed `factor`.
    """
    filename = "county_node_factor.csv"
    if os.path.exists(filename) and not refresh:
        county_node_factor = pd.read_csv(filename)
    else:
        county_node_factor = pd.read_csv(LOADS_URL+"wecc/node_estimate_cf.csv")\
            .rename({"cf":"factor"},axis=1)
        county_node_factor.to_csv(filename,index=False,header=True)
    return county_node_factor

def read_county_estimate(*,
    net:bool=True,
    ) -> pd.DataFrame:
    """Read the `eudoxys/loads` county hourly load estimate

    Arguments
    ---------
    - `net`: subtract the county rooftop PV (`county_dg_scaled.csv.gz`) from
      the gross load estimate, clipped at zero

    Returns
    -------
    - `pandas.DataFrame`: county load (not cached)
      - `timestamp`: UTC date/time of the beginning of the hour
      - ...: county/state name load (MW)

    Description
    -----------
    Reads `loads/wecc/wecc_estimate.csv.gz` (gross load, including load
    served by rooftop PV) and, if `net`, `loads/wecc/county_dg_scaled.csv.gz`
    (rooftop PV scaled to EIA small-scale solar estimates; counties missing
    from it have no DG) from `eudoxys/loads` at `LOADS_COMMIT`.
    """
    gross = pd.read_csv(LOADS_URL+"wecc/wecc_estimate.csv.gz",index_col=[0],parse_dates=[0]).copy()
    if not net:
        return gross.rename_axis("timestamp").reset_index()
    dg = pd.read_csv(LOADS_URL+"wecc/county_dg_scaled.csv.gz",index_col=[0],parse_dates=[0])
    dg = dg.reindex(index=gross.index,columns=gross.columns).fillna(0.0).copy()
    return (gross - dg.abs()).clip(lower=0.0).rename_axis("timestamp").reset_index()

def read_county_ba_load(*,
    refresh:bool|str=False,
    net:bool=True,
    precision:int=PRECISION,
    ) -> pd.DataFrame:
    """Read county hourly load disaggregated from EIA-930 BA demand

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `net`: use the county net load estimate (gross minus rooftop PV) to
      weight the counties (see `read_county_estimate`); only effective when
      creating or refreshing the data file

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: UTC date/time of the beginning of the hour
      - ...: county/state name load (MW)

    Description
    -----------
    Each BA's EIA-930 demand $D_b(t)$ is split among the counties it serves
    in proportion to the hourly contribution of each county's estimated load
    $L_c(t)$ to the BA, i.e., $L_c(t) f_{cb}$, where $f_{cb}$ is the county's
    BA participation factor (`read_county_ba`). The county load is the sum of
    its BA shares:

    $$X_c(t) = \\sum_b D_b(t) \\frac{f_{cb} L_c(t)}{\\sum_k f_{kb} L_k(t)}$$

    The result is expected to satisfy:

    1. for every EIA-930 BA and hour with demand, the county shares of the
       BA sum to $D_b(t)$, so the county total equals the EIA-930 total plus
       the uncalibrated shares of non-EIA-930 BAs;
    2. when $\\sum_k f_{kb} L_k(t) = 0$, the BA demand is split by the
       factors $f_{cb}$ alone;
    3. shares of BAs without EIA-930 demand (e.g., `SWPP`) keep the county
       estimate $f_{cb} L_c(t)$;
    4. hours without EIA-930 demand (the first 8 hours of 2018) are `NaN`
       for counties served by the missing BAs.

    Because EIA-930 demand is net of rooftop PV, the result is a net load.
    """
    filename = "county_ba_load.csv.gz"
    if os.path.exists(filename) and not refresh:
        return pd.read_csv(filename,parse_dates=[0])

    deps = refresh=="all"
    load = read_county_estimate(net=net).set_index("timestamp").reindex(hour_range)
    demand = read_ba_load(refresh=deps).set_index("timestamp").reindex(hour_range)
    factor = read_county_ba(refresh=deps).pivot_table(index="county_st",
        columns="ba",values="factor",aggfunc="sum",fill_value=0.0)
    missing = sorted(set(load.columns) - set(factor.index))
    if missing:
        warn(f"counties without BA factors are omitted: {', '.join(missing)}")
    counties = [x for x in load.columns if x in factor.index]
    load = load[counties]
    factor = factor.loc[counties]
    bas = list(factor.columns)
    nodemand = sorted(set(demand.columns) - set(bas))
    if nodemand:
        warn(f"EIA-930 BAs without counties are not allocated: {', '.join(nodemand)}")

    L = load.values                                   # hours x counties
    F = factor.values                                 # counties x BAs
    S = L @ F                                         # hours x BAs (BA estimate)
    D = demand.reindex(columns=bas).values            # hours x BAs (NaN if not in EIA-930)
    in930 = np.array([x in demand.columns for x in bas])
    with np.errstate(divide="ignore",invalid="ignore"):
        R = np.where(S > 0,D/S,0.0)                   # BA scale factor
    R[:,~in930] = 1.0                                 # non-EIA-930 BAs keep the estimate
    nodata = np.isnan(D) & in930                      # missing EIA-930 hours
    R[nodata] = 0.0
    result = L * (R @ F.T)
    # BA hours with zero estimated load: split demand by factors alone
    zero = (S <= 0) & in930 & ~nodata
    if zero.any():
        result += (np.where(zero,D,0.0) / F.sum(axis=0)) @ F.T
    # a county is NaN in an hour when any of its EIA-930 BAs has no data
    result[(nodata.astype(float) @ (F.T > 0)) > 0] = np.nan

    county_ba_load = pd.DataFrame(result,index=hour_range,columns=counties)\
        .rename_axis("timestamp").round(precision).reset_index()
    county_ba_load.to_csv(filename,index=False,header=True,compression="gzip")
    return county_ba_load

def read_node_ba_load(*,
    refresh:bool|str=False,
    precision:int=PRECISION,
    ) -> pd.DataFrame:
    """Read node hourly load disaggregated from EIA-930 BA demand

    Arguments
    ---------
    - `refresh`: force refresh of data file (`"all"` forces refresh of
      dependencies)

    - `precision`: data rounding precision

    Returns
    -------
    - `pandas.DataFrame`: contents of the data file
      - `timestamp`: UTC date/time of the beginning of the hour
      - ...: node geohash load (MW)

    Description
    -----------
    The node load is the sum of the county loads of `read_county_ba_load`
    allocated with the county-to-node factors of `read_county_node_factor`:

    $$N_n(t) = \\sum_c g_{cn} X_c(t)$$

    Because each county's factors sum to 1, the total node load equals the
    total county load. Only US counties are included; the Canadian and
    Mexican loads are not in EIA-930 and are not included (node `c2u6xt` is
    a Canadian node that receives the load of nearby US counties).
    """
    filename = "node_ba_load.csv.gz"
    if os.path.exists(filename) and not refresh:
        return pd.read_csv(filename,parse_dates=[0])

    county_load = read_county_ba_load(refresh=refresh=="all").set_index("timestamp")
    factor = read_county_node_factor(refresh=refresh=="all").pivot_table(index="county_st",
        columns="node",values="factor",aggfunc="sum",fill_value=0.0)
    missing = sorted(set(county_load.columns) - set(factor.index))
    if missing:
        warn(f"counties without node factors are omitted: {', '.join(missing)}")
    counties = [x for x in county_load.columns if x in factor.index]
    factor = factor.loc[counties,sorted(factor.columns)]
    values = county_load[counties]
    node_load = values.fillna(0.0).values @ factor.values
    # a node is NaN in an hour when any of its counties is NaN
    node_load[(values.isna().values.astype(float) @ (factor.values > 0)) > 0] = np.nan

    node_ba_load = pd.DataFrame(node_load,index=county_load.index,columns=factor.columns)\
        .round(precision).reset_index()
    node_ba_load.to_csv(filename,index=False,header=True,compression="gzip")
    return node_ba_load

def read_county_bus_map():
    """Read the county-to-bus mapping


    Arguments
    ---------

    Returns
    -------
    """
    raise NotImplemented("TODO")

def help_md(function:Callable|list[Callable]) -> dict[str,str]:
    """Compile help markdown string

    Arguments
    ---------
    - `function`: function or list of functions to document

    Returns
    -------
    - `dict`: mapping of function names and markdown documentation
    """
    if isinstance(function,list):
        return {x.__name__:help_md(x)[x.__name__] for x in function}
    args = ", ".join([f"{x}:{y.__name__ if hasattr(y,"__name__") else y}" for x,y in function.__annotations__.items() if x != "return"])
    retv = ", ".join([f"{y.__module__}.{y.__name__ if hasattr(y,"__name__") else y}" for x,y in function.__annotations__.items() if x == "return"])
    body =  function.__doc__.split("\n")
    body = [body[0]] + [x[(4 if x[0:4] == '    ' else 0):] for x in body[1:]]
    body = "\n".join(body)
    return {function.__name__:f"`{function.__name__}({args}) -> {retv}`\n\n{body}"}

if __name__ == "__main__":

    # pd.options.display.max_columns = None
    # pd.options.display.width = None

    period = pd.date_range(
        start="2020-08-01 00:00:00+0000",
        end="2020-08-31 23:00:00+0000",
        freq="1h")

    node_net = read_node_net().set_index("timestamp")
    print(read_node_offset(period,peak=node_net.sum(axis=1).max()+1000))

    refresh=False # read from the cached results
    # refresh=True # regenerate only the requested data from dependencies
    # refresh=None # regenerate all the data from original sources

    counties = read_counties(refresh=refresh)
    states = read_states(refresh=refresh)
    bus_gis = read_bus_gis(refresh=refresh)
    us_loads = read_bustype("load",country="US",refresh=refresh)

    node_dg = read_node_dg(refresh=refresh)
    node_total = read_node_total(refresh=refresh)
    node_net = read_node_net(refresh=refresh)
    node_project = read_node_project([1.1,1000],refresh=refresh)
    
    county_node_cf = read_county_node_cf(refresh=refresh)
    county_node_map = read_county_node_map(refresh=refresh)
    county_total = read_county_total(refresh=refresh)
    county_dg = read_county_dg(refresh=refresh)
    county_net = read_county_net(refresh=refresh)

    state_total = read_state_total(refresh=refresh)
    state_mwh = read_state_mwh(refresh=refresh)
    state_net = read_state_net(refresh=refresh)
    state_calibration = read_state_calibration(refresh=refresh)

    ba_load = read_ba_load(refresh=refresh)
    county_ba = read_county_ba(refresh=refresh)
    county_node_factor = read_county_node_factor(refresh=refresh)
    county_ba_load = read_county_ba_load(refresh=refresh)
    node_ba_load = read_node_ba_load(refresh=refresh)
    # state_offset = read_state_offset(refresh=refresh)


    #
    # Read county contribution factors (county_cf)
    #
    # county_cf = pd.read_csv("county_cf.csv",index_col=[0])
    # county_cf.index = pd.DatetimeIndex(county_cf.index,tz="UTC")
    # county_cf.index.name="timestamp"
    # print(county_cf)

