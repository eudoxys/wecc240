"""Build wecc240/wecc240_2020.py: the WECC 240 case at an hour of 2020

Syntax: python3 wecc240/build_wecc240_2020.py [-t TIMESTAMP] [-l FOLDER] [-g FOLDER] [-r FOLDER] [-b FOLDER] [-e CSV]

Options
-------
- `-t TIMESTAMP`, `--timestamp TIMESTAMP`: hour of the load and generation
  data (hour-beginning; UTC unless the timestamp gives its time zone), or
  `peak` for the hour of the peak CAISO net load in `YEAR`, or `peak:YEAR`
  for another year (default `peak`, which is 2020-09-07 01:00 UTC, 18:00
  PDT on 6 September 2020)
- `-l FOLDER`, `--loads FOLDER`: `loads/wecc` folder of `eudoxys/loads`
  (default `LOADS_LOCAL` in a sibling clone, otherwise `LOADS_URL`); the
  CAISO load is read from its sibling folder `loads/caiso`
- `-g FOLDER`, `--generation FOLDER`: `data/wecc` folder of
  `eudoxys/generation` (default `GENERATION_LOCAL` in a sibling clone,
  otherwise `GENERATION_URL`)
- `-r FOLDER`, `--regrow FOLDER`: root of `slacgismo/regrow` (default
  `REGROW_LOCAL` in a sibling clone, otherwise `REGROW_URL`)
- `-b FOLDER`, `--batteries FOLDER`: `data/batteries/processed` folder of
  `slacgismo/regrow` (default that folder under `--regrow`)
- `-e CSV`, `--form930 CSV`: Form 930 hourly load of the WECC balancing
  authorities (default `data/form930_load_{year}.csv.gz`, written by
  `data/form930_load.py`)
- `-x`, `--raise-ratings`: if the dispatch OPF fails with the 2018 branch
  ratings, relax `rateA` by the factors of `RELAX` until it solves and
  raise the ratings of the branches it loads above `rateA` (default: fail)

Description
-----------

Reads `wecc240/wecc240_2018.py`, replaces its US generator fleet with the
`eudoxys/generation` node fleet at the hour, sets the bus loads and the generator outputs to
the hour, and writes `wecc240/wecc240_2020.py` (case name `wecc240_2020`).
Buses are grouped into nodes by their 6-character geohash in
`wecc240/gis/wecc240.csv`.

```mermaid
flowchart LR
    est[/"loads: wecc_estimate.csv.gz"/] -->|county gross MW| sub((-))
    dg[/"loads: county_dg.csv.gz"/] -->|county DG MW| sub
    sub -->|county net MW| mul((x))
    cf[/"loads: node_estimate_cf.csv"/] --> mul
    mul -->|Σ county| add((+))
    foreign[/"Canada/*.csv Mexico/*.csv"/] -->|load_MW| add
    add -->|node net load| b2020([build_wecc240_2020.py])
    form930[/"data/form930_load_{year}.csv.gz"/] -->|BA peaks| scale((scale))
    eia860[/"regrow: EIA-860 plants, generators"/] -->|county BA shares| scale
    scale -->|county factors| mul
    capacity[/"generation: node_capacity_*.csv.gz"/] -->|node dispatchable MW| b2020
    actual[/"generation: node_actual_*.csv.gz"/] -->|node MW| b2020
    foreign -->|dispatch_MW| b2020
    bounds[/"regrow: node_reactive_bounds_by_year.csv"/] -->|node battery P, Q limits| b2020
    bgen[/"regrow: node_generation_by_month.csv"/] -->|node battery net MWh| b2020
    c2018[wecc240_2018.py] --> b2020
    types[/wecc240_gentypes.csv/] -->|costs| b2020
    b2020 --> c2020[wecc240_2020.py]
```

Hour
----

The default hour is that of the peak CAISO net load in `YEAR`: the CAISO
EMS hourly load (`loads/caiso/{year}.csv` in `eudoxys/loads`, hour ending,
Pacific time) less the CAISO solar and wind output. The CAISO solar and wind
output is the county output in `actual_solar.csv.gz` and
`actual_wind.csv.gz` of `eudoxys/generation` times the share of each
county's solar or wind nameplate capacity that is in the CAISO balancing
authority (`CISO`) in the EIA-860 fleet of the year.

Loads
-----

1. The net load of each WECC county is its calibrated gross load
   (`wecc_estimate.csv.gz` in `eudoxys/loads`) less its distributed solar
   generation (`county_dg.csv.gz`, the DG that calibration adds to retail
   energy), so that its monthly energy is the EIA 861M retail energy.

2. Each county's net load is scaled so that each balancing authority's
   annual peak matches its Form 930 demand peak of the year
   (`data/form930_load_{year}.csv.gz`, from `eia.Form930` of `eudoxys/eia`).
   A county's load is split among balancing authorities by the nameplate
   share of its EIA-860 plants' balancing authorities (among those in the
   Form 930 file); a county with no such plant takes the split of the
   counties sharing its `load` node in `wecc240/data/county_node_map.csv`,
   else its state's. Each authority's factor is its Form 930 peak over the
   peak of its modeled load (the sum of its county shares over the year),
   and a county's factor is the share-weighted mean of its authorities'
   factors. Form 930 hours that are not positive or are spikes (above
   `SPIKE_HOURS` times the median of the 9 hours around them, or
   `SPIKE_DAYS` times the median of the same hour on the 7 days around
   them) are dropped before taking the peak; an authority with less than
   `MIN_HOURS` of the year left (PSEI in 2020) keeps a factor of 1.

3. The county net loads are allocated to nodes with the contribution
   factors of `node_estimate_cf.csv` (as `node_estimate.py` does in
   `eudoxys/loads`). The `load_MW` of the Canadian and Mexican node files
   (`FOREIGN`) is added to those nodes.

4. A node's load is split among its buses in proportion to their `PD` in
   the 2018 case, and each bus keeps its 2018 `QD/PD` ratio (`DESIGN.md`
   decision 9). Buses of nodes that get no load are set to `PD = QD = 0`.

Generator fleet
---------------

1. The fleet is the EIA-860 generators of the year of the hour in plants of
   the WECC NERC region (`data/batteries/raw/EIA860` of `slacgismo/regrow`):
   the `Operable` generators that started operating before the end of the
   month of the hour, and the retired generators that started before and
   retired after it. A unit's category is that of its energy source and
   prime mover as in `generation.fuels` of `eudoxys/generation` (`FUELS`,
   `PRIME_MOVERS`).

2. The node capacity (`node_capacity_{category}.csv.gz`) and output
   (`node_actual_{category}.csv.gz`) of `eudoxys/generation` at the hour are
   used as they are: `eudoxys/generation` maps each county to the `gen` node
   of `wecc240/data/county_node_map.csv`. The EIA-860 fleet is used only for
   the CAISO solar and wind shares and the county balancing authority
   shares.

3. The 2018 generators of the US nodes that have a category (all but `SC`
   synchronous condensers and `ND` absorbing units) are removed, and each
   node and category with capacity or output gets one generator, at the
   node bus that had the most 2018 generating capacity (else its
   highest-voltage bus), with the bus's 2018 `Vg`:

   - dispatchable categories (all but `NONDISPATCHABLE`, as
     `generation.fuels.DISPATCHABLE`): `Pmax` the node capacity, `Pmin = 0`
     (pumped storage: `-Pmax`), and `Pg` the node output (the power flow
     setpoint; the OPF redispatches between `Pmin` and `Pmax`);
   - non-dispatchable categories (solar, wind): `Pg = Pmax` the node output,
     `Pmin = 0`.

   The 2018 reactive power limits of the removed generators at a bus are
   given to the new generators at that bus in proportion to their `Pmax`.

4. Battery storage comes from `slacgismo/regrow` PR #91, not from
   `eudoxys/generation`: each node in `node_reactive_bounds_by_year.csv` for
   the year of the hour gets one generator with `Pmin = -max_charge_MW`,
   `Pmax = max_discharge_MW`, `Qmin = -reactive_MVAR`,
   `Qmax = reactive_MVAR` (PYPOWER has only a box, so the disc of the P-Q
   region is not represented), and `Pg` the node's mean net output in the
   month of the hour (`Net Gen (MWh)` of `node_generation_by_month.csv` over
   the hours of the month, limited to `Pmin`..`Pmax`; 0 where the node did
   not report).

5. The 2018 generators at the Canadian and Mexican nodes are kept and
   dispatched to the node file's `dispatch_MW` in proportion to their
   `Pmax`; Alberta (`c2u6xt`), which has none, gets a generator fixed at its
   `dispatch_MW`. US generation mapped to these nodes is added as above.

Costs
-----

A new generator gets the polynomial cost of the 2018 generators of its
category at its node (from their types in `wecc240_gentypes.csv`, weighted
by `Pmax`), else that of all 2018 generators of the category. Oil and other
have no NREL cost and get the cost of the most expensive 2018 gas type
(`PEAKER`); pumped storage, battery storage, the Alberta generator, solar,
wind and hydro cost 0.

Branch ratings, voltage setpoints and shunts are those of the 2018 case. The
script solves the power flow and fails if it does not converge; it reports
the slack generation, the buses outside their voltage limits and the number
of branches loaded above `rateA`, but does not change the case to remove
them.

Areas
-----

The areas are the EIA Form 930 balancing authorities: before saving, each
bus is put in the area of its code in `wecc240_ba.csv`
(`_areas.balancing_authorities`), areas are numbered in alphabetical order
of the codes, the `areas` rows get their default price reference buses, and
the geodata `BA` column is set to the code. Areas do not change the
solution.

Uses `_case.py`, `_dcline.py` and `_areas.py`.
"""

import argparse
import csv
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
from _case import Case # pylint: disable=wrong-import-position,import-error
from _areas import balancing_authorities # pylint: disable=wrong-import-position,import-error

YEAR = 2020
"""Year of the default hour (peak CAISO net load)"""

CATEGORIES = {
    "coal": ["C","E"],
    "natural_gas": ["G","CG","DG","EG","MG","NG","RG","SG","TG","WG"],
    "nuclear": ["N","NN"],
    "hydro": ["H","NH","SH"],
    "wind": ["W","NW","SW","R"],
    "solar": ["S","NP","P"],
    "geothermal": ["CE","NE"],
    "biomass": ["B","NB"],
    "oil": [],
    "other": [],
    "pumped_storage": [],
    }
"""Categories of the fleet (`generation.fuels.CATEGORIES` but battery storage)
and the 2018 generator type codes (PSS/E generator IDs) of each"""

UNCATEGORIZED = ["SC","ND"]
"""2018 generator types with no category, kept as in the 2018 case"""

NONDISPATCHABLE = ["solar","wind"]
"""Categories set from output, not capacity (`generation.fuels.DISPATCHABLE`)"""

MAX_LOADING = 0.8
"""Largest loading of a raised branch `rateA` (a 20% margin, as `build_wecc240_2018.py`)"""

RELAX = [1.0,1.25,1.5,2.0,3.0,5.0]
"""Factors on `rateA` tried in turn until the dispatch OPF solves (with `--raise-ratings`)"""

SPIKE_HOURS = 1.25
"""Largest Form 930 load over the median of the 9 hours around it"""

SPIKE_DAYS = 1.5
"""Largest Form 930 load over the median of the same hour on the 7 days around it"""

MIN_HOURS = 0.8
"""Smallest fraction of the year's hours with good Form 930 load for a peak"""

PEAKER = "TG"
"""2018 gas type whose cost is given to oil and other"""

FUELS = {
    **{x:"coal" for x in ("ANT","BIT","LIG","SUB","SGC","WC","RC","SC")},
    "NG": "natural_gas",
    **{x:"oil" for x in ("DFO","RFO","JF","KER","WO","PC")},
    "NUC": "nuclear",
    "WAT": "hydro",
    "GEO": "geothermal",
    **{x:"biomass" for x in ("AB","BLQ","LFG","MSB","MSW","OBG","OBL","OBS","SLW","WDL","WDS")},
    "MWH": "battery_storage",
    "SUN": "solar",
    "WND": "wind",
    }
"""EIA energy source code to category (`generation.fuels.FUELS`; others are `other`)"""

PRIME_MOVERS = {"PS":"pumped_storage","BA":"battery_storage","CE":"battery_storage",
    "FW":"battery_storage","ES":"battery_storage"}
"""EIA prime movers that set the category (`generation.fuels.PRIME_MOVERS`)"""

FOREIGN = {"c2c10y":"Canada","c2u6xt":"Canada","9mtzm4":"Mexico"}
"""Nodes outside the US and the folder holding their node file"""

LOADS_LOCAL = os.path.join(HERE,"..","..","loads","loads","wecc")
"""`eudoxys/loads` WECC folder in a sibling clone"""

LOADS_URL = "https://raw.githubusercontent.com/eudoxys/loads/main/loads/wecc"
"""`eudoxys/loads` WECC folder on GitHub"""

GENERATION_LOCAL = os.path.join(HERE,"..","..","generation","data","wecc")
"""`eudoxys/generation` WECC folder in a sibling clone"""

GENERATION_URL = "https://raw.githubusercontent.com/eudoxys/generation/main/data/wecc"
"""`eudoxys/generation` WECC folder on GitHub"""

REGROW_LOCAL = os.path.join(HERE,"..","..","regrow")
"""`slacgismo/regrow` sibling clone (with the `battery-data` branch of PR #91)"""

REGROW_URL = "https://raw.githubusercontent.com/slacgismo/regrow/" \
    "cf38a9cd48a5ece0011ee1b20be3140b380201dc"
"""`slacgismo/regrow` on GitHub (PR #91 head, `battery-data` branch)"""

def read(name):
    """Rows of a CSV file next to this script"""
    with open(os.path.join(HERE,name),newline="",encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def path(folder,*names):
    """Path or URL of a file in a folder"""
    return "/".join([folder,*names]) if "://" in folder else os.path.join(folder,*names)

def hour(folder,name,timestamp):
    """Row of an hourly CSV file (index `timestamp`) at an hour"""
    data = pd.read_csv(path(folder,name),index_col=0,parse_dates=[0])
    if timestamp not in data.index:
        raise ValueError(f"{name} has no row for {timestamp}")
    return data.loc[timestamp]

def fleet(regrow,timestamp):
    """EIA-860 WECC generators operating at an hour, with category, county and
    balancing authority (for the CAISO solar and wind shares)"""
    folder = path(regrow,"data","batteries","raw","EIA860",f"eia860{timestamp.year}")
    plants = pd.read_excel(path(folder,f"2___Plant_Y{timestamp.year}.xlsx"),header=1)
    plants = plants[plants["NERC Region"] == "WECC"].copy()
    for name in ("Latitude","Longitude"):
        plants[name] = pd.to_numeric(plants[name],errors="coerce")
    plants = plants.dropna(subset=["Latitude","Longitude"])
    sheets = pd.read_excel(path(folder,f"3_1_Generator_Y{timestamp.year}.xlsx"),
        sheet_name=["Operable","Retired and Canceled"],header=1)
    end = (timestamp.year,timestamp.month)
    def date(x,year,month):
        return list(zip(pd.to_numeric(x[year],errors="coerce"),pd.to_numeric(x[month],errors="coerce")))
    def started(x):
        return pd.Series([(y,m) <= end for y,m in date(x,"Operating Year","Operating Month")],index=x.index)
    operable = sheets["Operable"]
    retired = sheets["Retired and Canceled"]
    retired = retired[retired["Status"] == "RE"]
    retired = retired[[(y,m) > end for y,m in date(retired,"Retirement Year","Retirement Month")]]
    units = pd.concat([operable[started(operable)],retired[started(retired)]])
    units = units[units["Plant Code"].isin(plants["Plant Code"])].copy()
    units["category"] = [PRIME_MOVERS.get(str(p).strip(),FUELS.get(str(f).strip(),"other"))
        for p,f in zip(units["Prime Mover"],units["Energy Source 1"])]
    plants = plants.set_index("Plant Code")
    units["county_st"] = units["Plant Code"].map(plants["County"].str.strip() + " " + plants["State"])
    units["county"] = units["county_st"].str.casefold()
    units["ba"] = units["Plant Code"].map(plants["Balancing Authority Code"])
    units["MW"] = pd.to_numeric(units["Nameplate Capacity (MW)"],errors="coerce").fillna(0.0)
    return units

def caiso_peak(loads,generation,units,year):
    """Hour (UTC, hour-beginning) of the peak CAISO net load in a year"""
    data = pd.read_csv(path(loads,"..","caiso",f"{year}.csv"),usecols=[0,1,6])
    data.columns = ["date","he","load"]
    data = data.dropna(subset=["date","he","load"])
    local = pd.to_datetime(data["date"],format="%m/%d/%y") \
        + pd.to_timedelta(data["he"].astype(int)-1,unit="h")
    data.index = pd.DatetimeIndex(local).tz_localize("America/Los_Angeles",
        ambiguous="NaT",nonexistent="NaT").tz_convert("UTC")
    net = data.loc[data.index.notna(),"load"].astype(float)
    for cat in NONDISPATCHABLE:
        actual = pd.read_csv(path(generation,f"actual_{cat}.csv.gz"),index_col=0,parse_dates=[0])
        actual.columns = actual.columns.str.casefold()
        x = units[units["category"] == cat]
        share = x[x["ba"] == "CISO"].groupby("county")["MW"].sum() / x.groupby("county")["MW"].sum()
        caiso = (actual*share.reindex(actual.columns).fillna(0.0)).sum(axis=1)
        net = net - caiso.reindex(net.index).fillna(0.0)
    return net.idxmax(),net.max()

def county_net(loads,year):
    """County net loads (MW): calibrated gross load less DG, hourly over a year"""
    gross = pd.read_csv(path(loads,"wecc_estimate.csv.gz"),index_col=0,parse_dates=[0])
    dg = pd.read_csv(path(loads,"county_dg.csv.gz"),index_col=0,parse_dates=[0])
    gross = gross[gross.index.year == year]
    return gross.sub(dg.reindex(index=gross.index,columns=gross.columns).fillna(0.0))

def county_ba(units,counties,authorities):
    """Share of each county's load in each balancing authority: the nameplate
    share of the county's EIA-860 units by plant balancing authority, among
    `authorities`; counties with none take the split of the counties sharing
    their `load` node in `county_node_map.csv`, else their state's split"""
    x = units[units["ba"].isin(authorities)]
    def split(rows):
        mw = rows.groupby("ba")["MW"].sum()
        return mw/mw.sum() if mw.sum() > 0 else None
    loadnode = {r["county_st"].casefold():r["load"] for r in read(os.path.join("data","county_node_map.csv"))}
    result,source = {},{}
    for county in counties:
        key = county.casefold()
        shares = split(x[x["county"] == key])
        source[county] = "plants"
        if shares is None and key in loadnode:
            peers = [c for c,n in loadnode.items() if n == loadnode[key]]
            shares = split(x[x["county"].isin(peers)])
            source[county] = "load node"
        if shares is None:
            shares = split(x[x["county"].str.endswith(" " + key.rsplit(" ",1)[1])])
            source[county] = "state"
        if shares is None:
            raise ValueError(f"county {county} has no balancing authority")
        result[county] = shares
    return pd.DataFrame(result).T.fillna(0.0),source

def form930_peaks(form930):
    """Annual peak of each Form 930 load column without bad data: hours not
    above zero, more than `SPIKE_HOURS` times the median of the 9 hours
    around them, or more than `SPIKE_DAYS` times the median of the same hour
    on the 7 days around them, are dropped; columns with fewer than
    `MIN_HOURS` of the year's hours left have no peak (NaN)"""
    load = form930.where(form930 > 0)
    hours = load/load.rolling(9,center=True,min_periods=5).median()
    days = load/load.groupby(load.index.hour).transform(
        lambda x:x.rolling(7,center=True,min_periods=4).median())
    clean = load.where((hours <= SPIKE_HOURS) & (days <= SPIKE_DAYS))
    peaks = clean.max()
    peaks[clean.count() < MIN_HOURS*len(clean)] = float("nan")
    return peaks,load.count()-clean.count()

def ba_scale(net,shares,form930):
    """County load scale factors fitting each balancing authority's annual
    peak to Form 930 (1 for authorities without a Form 930 peak), and the
    authorities' modeled and Form 930 peaks"""
    model = net[shares.index].dot(shares)
    peak,dropped = form930_peaks(form930[shares.columns])
    peaks = pd.DataFrame({"model":model.max(),"form930":peak,"dropped":dropped})
    peaks["factor"] = (peaks["form930"]/peaks["model"]).fillna(1.0)
    return shares.dot(peaks["factor"]),peaks

def node_loads(loads,timestamp,net,scale):
    """Node net loads (MW) at an hour, with county scale factors"""
    if timestamp not in net.index:
        raise ValueError(f"wecc_estimate.csv.gz has no row for {timestamp}")
    net = net.loc[timestamp]*scale.reindex(net.columns).fillna(1.0)
    cf = pd.read_csv(path(loads,"node_estimate_cf.csv"))
    missing = sorted(set(cf["county_st"]) - set(net.index))
    if missing:
        raise ValueError(f"wecc_estimate.csv.gz has no load for {missing}")
    result = (cf["county_st"].map(net)*cf["cf"]).groupby(cf["node"]).sum()
    for node,folder in FOREIGN.items():
        load = hour(os.path.join(HERE,folder),f"{node}.csv",timestamp)["load_MW"]
        result[node] = result.get(node,0.0) + load
    return result

def node_generation(generation,timestamp):
    """Node capacity and output (MW) by category at an hour (`eudoxys/generation`
    `node_*` files, its county-to-node map), and the county totals"""
    capacity,output,county = {},{},{}
    for cat in CATEGORIES:
        for name,values in (("capacity",capacity),("actual",output)):
            row = hour(generation,f"node_{name}_{cat}.csv.gz",timestamp)
            for node,value in row.items():
                if value != 0:
                    values[(node,cat)] = float(value)
            county[(name,cat)] = float(hour(generation,f"{name}_{cat}.csv.gz",timestamp).sum())
    return capacity,output,county

def node_bus(rows,gens):
    """Bus of a node for a new generator: the bus with the most generating
    capacity, else the highest-voltage bus; and its voltage setpoint"""
    busset = {b[0] for b in rows}
    genbus = {}
    for g in gens:
        if g[0] in busset:
            genbus[g[0]] = genbus.get(g[0],0.0) + g[8]
    bus = max(genbus,key=genbus.get) if genbus else max(rows,key=lambda b:b[9])[0]
    vg = next((g[5] for g in gens if g[0] == bus),next(b[7] for b in rows if b[0] == bus))
    return bus,vg

def timestamp_of(value,loads,generation,regrow):
    """Hour of a `--timestamp` value, and the fleet of its year"""
    if value.startswith("peak"):
        year = int(value.split(":",1)[1]) if ":" in value else YEAR
        units = fleet(regrow,pd.Timestamp(f"{year}-12-01",tz="UTC"))
        when,peak = caiso_peak(loads,generation,units,year)
        print(f"peak CAISO net load {peak:.0f} MW at {when} "
            f"({when.tz_convert('America/Los_Angeles')})")
        if when.month != 12:
            units = fleet(regrow,when)
        return when,units
    when = pd.Timestamp(value)
    when = when.tz_localize("UTC") if when.tzinfo is None else when.tz_convert("UTC")
    return when,fleet(regrow,when)

def main():
    """Write wecc240/wecc240_2020.py"""
    parser = argparse.ArgumentParser(prog="build_wecc240_2020.py",
        description="Build the WECC 240 case at an hour of 2020")
    parser.add_argument("-t","--timestamp",default="peak",
        help="hour of the data (UTC unless given), or peak[:YEAR] for the peak CAISO net load")
    parser.add_argument("-l","--loads",help="eudoxys/loads loads/wecc folder")
    parser.add_argument("-g","--generation",help="eudoxys/generation data/wecc folder")
    parser.add_argument("-r","--regrow",help="slacgismo/regrow root folder")
    parser.add_argument("-b","--batteries",help="slacgismo/regrow data/batteries/processed folder")
    parser.add_argument("-x","--raise-ratings",action="store_true",
        help="relax rateA for the dispatch OPF and raise the ratings it overloads")
    parser.add_argument("-e","--form930",help="Form 930 hourly load CSV (default data/form930_load_{year}.csv.gz)")
    args = parser.parse_args()
    loads = args.loads or (LOADS_LOCAL if os.path.exists(LOADS_LOCAL) else LOADS_URL)
    generation = args.generation or (GENERATION_LOCAL if os.path.exists(GENERATION_LOCAL) else GENERATION_URL)
    regrow = args.regrow or (REGROW_LOCAL if os.path.exists(path(REGROW_LOCAL,"data","batteries")) else REGROW_URL)
    batteries = args.batteries or path(regrow,"data","batteries","processed")
    timestamp,units = timestamp_of(args.timestamp,loads,generation,regrow)

    case = Case.load(os.path.join(HERE,"wecc240_2018.py"))
    case.name = "wecc240_2020"
    geohash = {int(r["BUS_I"]):r["GEOHASH"] for r in read(os.path.join("gis","wecc240.csv"))}
    buses = case.tables["bus"]
    missing = [b[0] for b in buses if b[0] not in geohash]
    if missing:
        raise ValueError(f"buses {missing} are not in gis/wecc240.csv")
    nodes = {}
    for b in buses:
        nodes.setdefault(geohash[b[0]],[]).append(b)

    # loads
    form930 = pd.read_csv(args.form930 or os.path.join(HERE,"data",f"form930_load_{timestamp.year}.csv.gz"),
        index_col=0,parse_dates=[0])
    net = county_net(loads,timestamp.year)
    shares,ba_source = county_ba(units,net.columns,list(form930.columns))
    scale,peaks = ba_scale(net,shares,form930)
    load = node_loads(loads,timestamp,net,scale)
    unknown = sorted(set(load.index) - set(nodes))
    if unknown:
        raise ValueError(f"load nodes {unknown} have no bus")
    unloaded = []
    for node,rows in nodes.items():
        total = sum(b[2] for b in rows if b[2] > 0)
        if node not in load.index:
            unloaded.extend(b[0] for b in rows if b[2] != 0 or b[3] != 0)
            for b in rows:
                b[2],b[3] = 0.0,0.0
            continue
        if total == 0:
            raise ValueError(f"node {node} has load but no bus with PD > 0")
        for b in rows:
            pd_new = load[node]*b[2]/total if b[2] > 0 else 0.0
            b[3] = b[3]*pd_new/b[2] if b[2] > 0 else b[3]
            b[2] = pd_new

    # 2018 generators: categories, costs, buses and reactive limits
    types = {r["type"]:[float(r[x]) for x in ("c2","c1","c0")] for r in read("wecc240_gentypes.csv")}
    ids = [r["id"] for r in read("wecc240_cost.csv")]
    gens = case.tables["gen"]
    if len(ids) != len(gens):
        raise ValueError(f"wecc240_cost.csv has {len(ids)} rows for {len(gens)} generators")
    category = {t:c for c,x in CATEGORIES.items() for t in x}
    gencat = []
    for n,gid in enumerate(ids):
        gtype = gid.rsplit("_",1)[1]
        if gtype not in category and gtype not in UNCATEGORIZED:
            raise ValueError(f"generator {n+1} type {gtype} has no category")
        gencat.append(category.get(gtype))
    gentype = [gid.rsplit("_",1)[1] for gid in ids]
    def mean_cost(rows):
        weight = sum(x for x,_ in rows)
        return [round(sum(x*y[k] for x,y in rows)/weight,6) for k in range(3)] if weight > 0 else None
    costs = {c:mean_cost([(g[8],types[t]) for g,t,x in zip(gens,gentype,gencat) if x == c]) or [0.0,0.0,0.0]
        for c in CATEGORIES}
    costs["oil"] = costs["other"] = types[PEAKER]
    nodecosts = {}
    for node,rows in nodes.items():
        busset = {b[0] for b in rows}
        for cat in CATEGORIES:
            cost = mean_cost([(g[8],types[t]) for g,t,x in zip(gens,gentype,gencat) if x == cat and g[0] in busset])
            if cost:
                nodecosts[(node,cat)] = cost
    abroad = {b[0] for x in FOREIGN for b in nodes[x]}
    sites = {node:node_bus(rows,gens) for node,rows in nodes.items()}
    removed = [n for n,(g,c) in enumerate(zip(gens,gencat)) if c is not None and g[0] not in abroad]
    qlimits = {}
    for n in removed:
        q = qlimits.setdefault(geohash[gens[n][0]],[0.0,0.0])
        q[0] += gens[n][3]
        q[1] += gens[n][4]
    before = {c:sum(gens[n][8] for n in removed if gencat[n] == c) for c in CATEGORIES}
    case.delete_rows("gen",removed)
    for n in reversed(removed):
        del gencat[n]
    gencat = ["foreign" if c is not None else None for c in gencat]

    # US fleet
    capacity,output,county = node_generation(generation,timestamp)
    unknown = sorted({n for n,_ in capacity} - set(nodes))
    if unknown:
        raise ValueError(f"generation nodes {unknown} have no bus")
    added = []
    for (node,cat) in sorted(set(capacity) | set(output)):
        cap,act = capacity.get((node,cat),0.0),output.get((node,cat),0.0)
        if cat in NONDISPATCHABLE:
            pg,pmax,pmin = max(act,0.0),max(act,0.0),min(act,0.0)
        else:
            pg,pmax = act,max(cap,act)
            pmin = -pmax if cat == "pumped_storage" else min(act,0.0)
        if pmax == 0 and pmin == 0:
            continue
        bus,vg = sites[node]
        index = case.add_row("gen",{"bus":bus,"Pg":pg,"Qmax":0.0,"Qmin":0.0,
            "Vg":vg,"mBase":case.baseMVA,"status":1,"Pmax":pmax,"Pmin":pmin})
        cost = [0.0,0.0,0.0] if cat == "pumped_storage" else nodecosts.get((node,cat),costs[cat])
        case.tables["gencost"][index] = [2,0.0,0.0,3,",".join(f"{x:g}" for x in cost)]
        gencat.insert(index,cat)
        added.append((node,cat,bus,pg,pmax))
    condensers = []
    for node,(qmax,qmin) in qlimits.items():
        members = [g for g,c in zip(gens,gencat) if geohash[g[0]] == node and c in CATEGORIES]
        pmax = sum(g[8] for g in members)
        for g in members:
            share = g[8]/pmax if pmax > 0 else 1/len(members)
            g[3],g[4] = qmax*share,qmin*share
        if not members and (qmax != 0 or qmin != 0):
            bus,vg = sites[node]
            index = case.add_row("gen",{"bus":bus,"Pg":0.0,"Qmax":qmax,"Qmin":qmin,
                "Vg":vg,"mBase":case.baseMVA,"status":1,"Pmax":0.0,"Pmin":0.0})
            case.tables["gencost"][index] = [2,0.0,0.0,3,"0,0,0"]
            gencat.insert(index,"condenser")
            condensers.append((node,bus,qmin,qmax))

    # foreign generation
    for node,folder in FOREIGN.items():
        dispatch = hour(os.path.join(HERE,folder),f"{node}.csv",timestamp)["dispatch_MW"]
        rows = nodes[node]
        members = [g for g,c in zip(gens,gencat) if c == "foreign" and g[0] in {b[0] for b in rows}]
        pmax = sum(g[8] for g in members)
        for g in members:
            g[1] = dispatch*(g[8]/pmax if pmax > 0 else 1/len(members))
            g[8] = max(g[8],g[1])
        if not members and dispatch != 0:
            bus = max(rows,key=lambda b:b[9])
            index = case.add_row("gen",{"bus":bus[0],"Pg":dispatch,"Qmax":0.0,"Qmin":0.0,
                "Vg":bus[7],"mBase":case.baseMVA,"status":1,"Pmax":dispatch,"Pmin":dispatch})
            case.tables["gencost"][index] = [2,0.0,0.0,3,"0,0,0"]
            gencat.insert(index,"foreign")
            added.append((node,"foreign",bus[0],dispatch,dispatch))

    # battery storage
    bounds = pd.read_csv(path(batteries,"node_reactive_bounds_by_year.csv"))
    bounds = bounds[bounds["Year"] == timestamp.year].set_index("geohash")
    if bounds.empty or bounds.index.duplicated().any():
        raise ValueError(f"node_reactive_bounds_by_year.csv has no unique rows for {timestamp.year}")
    unknown = sorted(set(bounds.index) - set(nodes))
    if unknown:
        raise ValueError(f"battery nodes {unknown} have no bus")
    energy = pd.read_csv(path(batteries,"node_generation_by_month.csv"))
    energy = energy[(energy["Year"] == timestamp.year) & (energy["Month"] == timestamp.month)]
    energy = energy.set_index("geohash")["Net Gen (MWh)"]
    hours = timestamp.days_in_month*24
    storage = []
    for node,row in bounds.iterrows():
        pmin,pmax = -float(row["max_charge_MW"]),float(row["max_discharge_MW"])
        qmax = float(row["reactive_MVAR"])
        net = energy.get(node,float("nan"))
        value = 0.0 if pd.isna(net) else min(max(net/hours,pmin),pmax)
        bus,vg = sites[node]
        index = case.add_row("gen",{"bus":bus,"Pg":value,"Qmax":qmax,"Qmin":-qmax,
            "Vg":vg,"mBase":case.baseMVA,"status":1,"Pmax":pmax,"Pmin":pmin})
        case.tables["gencost"][index] = [2,0.0,0.0,3,"0,0,0"]
        gencat.insert(index,"battery_storage")
        storage.append((node,bus,pmin,pmax,qmax,value,"no report" if pd.isna(net) else ""))

    # dispatch: OPF of the dispatchable generators with the others fixed,
    # with branch rateA relaxed by the first factor of RELAX that solves
    dispatchable = [c in CATEGORIES and c not in NONDISPATCHABLE for c in gencat]
    saved = [(g[8],g[9]) for g in gens]
    for g,d in zip(gens,dispatchable):
        if not d:
            g[8] = g[9] = g[1]
    branches = case.tables["branch"]
    rates = [br[5] for br in branches]
    for factor in RELAX if args.raise_ratings else [1.0]:
        for br,rate in zip(branches,rates):
            br[5] = rate*factor
        opf = case.solve("opf")
        if opf["success"]:
            break
    else:
        raise ValueError("dispatch OPF failed" + (f" with rateA up to {RELAX[-1]} times"
            if args.raise_ratings else " with the 2018 ratings (--raise-ratings relaxes them)"))
    for br,rate in zip(branches,rates):
        br[5] = rate
    voltage = {x["bus_i"]:(x["Vm"],x["Va"]) for x in opf["bus"]}
    for b in buses:
        b[7],b[8] = voltage[b[0]]
    for g,(pmax,pmin),x in zip(gens,saved,opf["gen"]):
        if g[0] != x["bus"]:
            raise ValueError("OPF generator results are not in case order")
        if g[7]:
            g[1],g[2],g[5] = x["Pg"],x["Qg"],voltage[g[0]][0]
        g[8],g[9] = pmax,pmin

    result = case.solve("pf")
    if not result["success"]:
        raise ValueError("power flow failed")
    raised = []
    for br,x in zip(branches,result["branch"]):
        if args.raise_ratings and br[5] > 0 and x["loading_pct"] is not None and x["loading_pct"] > 100:
            rate = float(math.ceil(br[5]*x["loading_pct"]/100/MAX_LOADING))
            raised.append((br[0],br[1],br[5],rate))
            br[5] = rate
            br[6] = max(br[6],rate)
            br[7] = max(br[7],rate)
    result = case.solve("pf")
    if not result["success"]:
        raise ValueError("power flow failed")
    check = case.solve("opf")
    areas = balancing_authorities(case)
    errors = [x["message"] for x in case.validate() if x["level"] == "error"]
    if errors:
        raise ValueError("; ".join(errors))
    case.save(os.path.join(HERE,"wecc240_2020.py"))

    ref = {b[0] for b in buses if b[1] == 3}
    slack = sum(g["Pg"] for g in result["gen"] if g["bus"] in ref) \
        - sum(g[1] for g in gens if g[0] in ref)
    overloaded = sum(1 for x in result["branch"] if x["loading_pct"] is not None and x["loading_pct"] > 100)
    vmax = max(x["Vm"] for x in result["bus"])
    vmin = min(x["Vm"] for x in result["bus"])
    limits = {b[0]:(b[12],b[11]) for b in buses}
    outside = [f"{x['bus_i']} ({x['Vm']:.3f})" for x in result["bus"]
        if not limits[x["bus_i"]][0] <= x["Vm"] <= limits[x["bus_i"]][1]]
    print(f"wrote wecc240/wecc240_2020.py at {timestamp} ({timestamp.tz_convert('America/Los_Angeles')}): "
        f"{case.size()}")
    print(f"  load {sum(b[2] for b in buses):.0f} MW at {len(load)} nodes; "
        f"buses set to no load: {unloaded}")
    print(f"  county loads scaled to Form 930 {timestamp.year} balancing authority peaks "
        f"(county splits from plants {sum(v == 'plants' for v in ba_source.values())}, load node "
        f"{sum(v == 'load node' for v in ba_source.values())}, state {sum(v == 'state' for v in ba_source.values())}):")
    for ba,row in peaks.iterrows():
        print(f"    {ba:5s} model peak {row['model']:8.0f} MW, Form 930 {row['form930']:8.0f} MW "
            f"({row['dropped']:.0f} bad hours), factor {row['factor']:.3f}")
    print(f"  generation {sum(g[1] for g in gens):.0f} MW scheduled, slack picked up {slack:.0f} MW, "
        f"losses {result['losses_MW']:.0f} MW")
    print("  US fleet by category, MW (2018 Pmax -> 2020 Pmax, output in the data):")
    for cat in CATEGORIES:
        rows = [x for x in added if x[1] == cat]
        print(f"    {cat:16s} {before[cat]:9.1f} -> {sum(x[4] for x in rows):9.1f}, "
            f"{sum(x[3] for x in rows):9.1f} ({len(rows)} generators; county data "
            f"{county[('capacity',cat)]:.1f}, {county[('actual',cat)]:.1f})")
    print(f"  {len(condensers)} nodes whose 2018 generators left no fleet generator keep their reactive "
        "limits as P = 0 generators: " + ", ".join(f"{n} bus {b} ({q0:.0f}..{q1:.0f} MVAr)" for n,b,q0,q1 in condensers))
    print(f"  {len(storage)} battery storage generators "
        f"({sum(x[3] for x in storage):.1f} MW discharge, {-sum(x[2] for x in storage):.1f} MW charge, "
        f"{sum(x[5] for x in storage):.1f} MW scheduled)")
    print(f"  dispatch OPF solved with rateA x{factor:g}; rateA raised on {len(raised)} branches "
        "loaded above it: " + ", ".join(f"{f}-{t} {a:g}->{b:g}" for f,t,a,b in raised))
    print(f"  {len(areas)} areas (EIA-930 balancing authorities from wecc240_ba.csv): "
        + ", ".join(f"{n} {ba}" for ba,n in areas.items()))
    print(f"  OPF of the saved case: {'solved' if check['success'] else 'FAILED'}")
    print(f"  power flow: Vm {vmin:.3f}-{vmax:.3f} pu, buses outside Vmin-Vmax: {outside}; "
        f"{overloaded} branches above rateA")

if __name__ == "__main__":
    main()
