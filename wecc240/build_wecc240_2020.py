"""Build wecc240/wecc240_2020.py: the WECC 240 case at 1 January 2020 00:00 UTC

Syntax: python3 wecc240/build_wecc240_2020.py [-t TIMESTAMP] [-l FOLDER] [-g FOLDER] [-b FOLDER]

Options
-------
- `-t TIMESTAMP`, `--timestamp TIMESTAMP`: hour of the snapshot, UTC
  (default `TIMESTAMP`, 2020-01-01 00:00:00+00:00)
- `-l FOLDER`, `--loads FOLDER`: `loads/wecc` folder of `eudoxys/loads`
  (default `LOADS_LOCAL` in a sibling clone, otherwise `LOADS_URL`)
- `-g FOLDER`, `--generation FOLDER`: `data/wecc` folder of
  `eudoxys/generation` (default `GENERATION_LOCAL` in a sibling clone,
  otherwise `GENERATION_URL`)
- `-b FOLDER`, `--batteries FOLDER`: `data/batteries/processed` folder of
  `slacgismo/regrow` (default `BATTERIES_LOCAL` in a sibling clone,
  otherwise `BATTERIES_URL`)

Description
-----------

Reads `wecc240/wecc240_2018.py`, sets the bus loads and the generator
outputs to the given hour, and writes `wecc240/wecc240_2020.py` (case name
`wecc240_2020`). Buses are grouped into nodes by their 6-character geohash
in `wecc240/gis/wecc240.csv`.

```mermaid
flowchart LR
    est[/"loads: wecc_estimate.csv.gz"/] -->|county gross MW| sub((-))
    dg[/"loads: county_dg.csv.gz"/] -->|county DG MW| sub
    sub -->|county net MW| mul((x))
    cf[/"loads: node_estimate_cf.csv"/] --> mul
    mul -->|Σ county| add((+))
    foreign[/"Canada/*.csv Mexico/*.csv"/] -->|load_MW| add
    add -->|node net load| b2020([build_wecc240_2020.py])
    actual[/"generation: node_actual_*.csv.gz"/] -->|node MW by category| b2020
    cap[/"generation: node_capacity_*.csv.gz"/] -->|node capacity by category| b2020
    foreign -->|dispatch_MW| b2020
    bounds[/"regrow: node_reactive_bounds_by_year.csv"/] -->|node battery P, Q limits| b2020
    bgen[/"regrow: node_generation_by_month.csv"/] -->|node battery net MWh| b2020
    c2018[wecc240_2018.py] --> b2020
    types[/wecc240_gentypes.csv/] -->|costs of new generators| b2020
    b2020 --> c2020[wecc240_2020.py]
```

Loads
-----

1. The net load of each WECC county is its calibrated gross load
   (`wecc_estimate.csv.gz` in `eudoxys/loads`) less its distributed solar
   generation (`county_dg.csv.gz`, the DG that calibration adds to retail
   energy), so that its monthly energy is the EIA 861M retail energy.

2. The county net loads are allocated to nodes with the contribution
   factors of `node_estimate_cf.csv` (as `node_estimate.py` does in
   `eudoxys/loads`). The `load_MW` of the Canadian and Mexican node files
   (`FOREIGN`) is added to those nodes.

3. A node's load is split among its buses in proportion to their `PD` in
   the 2018 case, and each bus keeps its 2018 `QD/PD` ratio (`DESIGN.md`
   decision 9). Buses of nodes that get no load are set to `PD = QD = 0`.

Generation
----------

1. A generator's category is the EIA fuel category of its type (the PSS/E
   generator ID at the end of its `id` in `wecc240_cost.csv`), as given by
   `CATEGORIES` (see "Generator types" in `wecc240/README.md`). Types `SC`
   (synchronous condensers) and `ND` (absorbing units) have no category and
   are left as in the 2018 case.

2. The net generation of each US node and category at the hour is read
   from `node_actual_{category}.csv.gz` of `eudoxys/generation`. It is
   split among the node's generators of that category in proportion to
   their `Pmax` (equally if all are 0); generators of a category with no
   generation at their node get `Pg = 0`. `Pmax` is raised to `Pg` where
   lower, and `Pmin` lowered to `Pg` where higher.

3. A node and category with nonzero generation but no generator of that
   category in the case gets a new generator at the node bus with the most
   generating capacity (else its highest-voltage bus), with `Pmax` the
   node's capacity in `node_capacity_{category}.csv.gz`, `Pmin = min(0,Pg)`,
   no reactive power range, and `Vg` of the bus.

4. Solar and wind generators get `Pmax = Pg` (the resource available at the
   hour). Categories with no NREL cost (`FIXED`: oil, other and pumped
   storage) are fixed at their output (`Pmin = Pmax = Pg`) with zero cost.

5. The generators at the Canadian and Mexican nodes are dispatched to the
   node file's `dispatch_MW` in proportion to their `Pmax`.

Battery storage
---------------

Battery storage comes from the battery data of `slacgismo/regrow` PR #91
(EIA-860 and EIA-923, WECC, 2018-2022), not from the `battery_storage`
category of `eudoxys/generation`. Each node in
`node_reactive_bounds_by_year.csv` for the year of the hour gets one
generator at the node bus chosen as in step 3, with

- `Pmin = -max_charge_MW` and `Pmax = max_discharge_MW`;
- `Qmin = -reactive_MVAR` and `Qmax = reactive_MVAR` (PYPOWER has only a
  box, so the disc of the P-Q region is not represented; Q limits apply
  only where the bus is a PV bus);
- `Pg` the node's mean net output in the month of the hour,
  `Net Gen (MWh)` of `node_generation_by_month.csv` over the hours of the
  month, limited to `Pmin`..`Pmax`; 0 where the node did not report
  (`NaN`).

Costs
-----

Existing generators keep their 2018 cost by type (`build_wecc240_2018.py`).
A new generator gets the cost of its category: the polynomial costs of the
category's types in `wecc240_gentypes.csv`, averaged over the category's
generators in the 2018 case weighted by `Pmax`. `FIXED` categories and
battery storage cost 0.

Branch ratings, voltage setpoints and shunts are those of the 2018 case. The
script solves the power flow and fails if it does not converge; it reports
the slack generation, the buses outside their voltage limits and the number
of branches loaded above `rateA`, but does not change the case to remove
them.

Uses `_case.py` and `_dcline.py`.
"""

import argparse
import csv
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
from _case import Case # pylint: disable=wrong-import-position,import-error

TIMESTAMP = "2020-01-01 00:00:00+00:00"
"""Default hour of the snapshot (UTC)"""

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
"""Generator type codes (PSS/E generator IDs) of each `eudoxys/generation` category"""

UNCATEGORIZED = ["SC","ND"]
"""Generator types with no category, left as in the 2018 case"""

VARIABLE = ["solar","wind"]
"""Categories whose `Pmax` is the output at the hour"""

FIXED = ["oil","other","pumped_storage"]
"""Categories with no NREL cost, fixed at their output at zero cost"""

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

BATTERIES_LOCAL = os.path.join(HERE,"..","..","regrow","data","batteries","processed")
"""`slacgismo/regrow` battery data folder in a sibling clone"""

BATTERIES_URL = "https://raw.githubusercontent.com/slacgismo/regrow/" \
    "cf38a9cd48a5ece0011ee1b20be3140b380201dc/data/batteries/processed"
"""`slacgismo/regrow` battery data folder on GitHub (PR #91 head, `battery-data` branch)"""

def read(name):
    """Rows of a CSV file next to this script"""
    with open(os.path.join(HERE,name),newline="",encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def path(folder,name):
    """Path or URL of a file in a folder"""
    return f"{folder}/{name}" if "://" in folder else os.path.join(folder,name)

def hour(folder,name,timestamp):
    """Row of an hourly CSV file (index `timestamp`) at an hour"""
    data = pd.read_csv(path(folder,name),index_col=0,parse_dates=[0])
    if timestamp not in data.index:
        raise ValueError(f"{name} has no row for {timestamp}")
    return data.loc[timestamp]

def node_loads(loads,timestamp):
    """Node net loads (MW) at an hour"""
    gross = hour(loads,"wecc_estimate.csv.gz",timestamp)
    dg = hour(loads,"county_dg.csv.gz",timestamp)
    net = gross.sub(dg.reindex(gross.index).fillna(0.0))
    cf = pd.read_csv(path(loads,"node_estimate_cf.csv"))
    missing = sorted(set(cf["county_st"]) - set(net.index))
    if missing:
        raise ValueError(f"wecc_estimate.csv.gz has no load for {missing}")
    result = (cf["county_st"].map(net)*cf["cf"]).groupby(cf["node"]).sum()
    for node,folder in FOREIGN.items():
        load = hour(os.path.join(HERE,folder),f"{node}.csv",timestamp)["load_MW"]
        result[node] = result.get(node,0.0) + load
    return result

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

def main():
    """Write wecc240/wecc240_2020.py"""
    parser = argparse.ArgumentParser(prog="build_wecc240_2020.py",
        description="Build the WECC 240 case at an hour of 2020")
    parser.add_argument("-t","--timestamp",default=TIMESTAMP,help="hour of the snapshot (UTC)")
    parser.add_argument("-l","--loads",help="eudoxys/loads loads/wecc folder")
    parser.add_argument("-g","--generation",help="eudoxys/generation data/wecc folder")
    parser.add_argument("-b","--batteries",help="slacgismo/regrow data/batteries/processed folder")
    args = parser.parse_args()
    timestamp = pd.Timestamp(args.timestamp)
    timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
    loads = args.loads or (LOADS_LOCAL if os.path.exists(LOADS_LOCAL) else LOADS_URL)
    generation = args.generation or (GENERATION_LOCAL if os.path.exists(GENERATION_LOCAL) else GENERATION_URL)
    batteries = args.batteries or (BATTERIES_LOCAL if os.path.exists(BATTERIES_LOCAL) else BATTERIES_URL)

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
    load = node_loads(loads,timestamp)
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

    # generator categories
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

    # category costs of new generators (Pmax-weighted over the 2018 generators)
    costs = {c:[0.0,0.0,0.0] for c in CATEGORIES}
    for cat in CATEGORIES:
        rows = [(g[8],types[gid.rsplit("_",1)[1]]) for g,gid,c in zip(gens,ids,gencat) if c == cat]
        weight = sum(x for x,_ in rows)
        if weight > 0 and cat not in FIXED:
            costs[cat] = [round(sum(x*y[k] for x,y in rows)/weight,6) for k in range(3)]

    # US generation by node and category
    abroad = {b[0] for x in FOREIGN for b in nodes[x]}
    def tally():
        return {c:sum(g[1] for g,x in zip(gens,gencat) if x == c and g[0] not in abroad) for c in CATEGORIES}
    before = tally()
    added = []
    for cat in CATEGORIES:
        actual = hour(generation,f"node_actual_{cat}.csv.gz",timestamp)
        capacity = hour(generation,f"node_capacity_{cat}.csv.gz",timestamp)
        unknown = sorted(set(actual[actual != 0].index) - set(nodes))
        if unknown:
            raise ValueError(f"{cat} generation nodes {unknown} have no bus")
        for node,rows in nodes.items():
            if node in FOREIGN:
                continue
            busset = {b[0] for b in rows}
            members = [n for n,(g,c) in enumerate(zip(gens,gencat)) if c == cat and g[0] in busset]
            value = float(actual.get(node,0.0))
            if members:
                pmax = sum(gens[n][8] for n in members)
                for n in members:
                    g = gens[n]
                    g[1] = value*(g[8]/pmax if pmax > 0 else 1/len(members))
                    if cat in VARIABLE:
                        g[8],g[9] = max(g[1],0.0),min(g[9],g[1])
                    else:
                        g[8],g[9] = max(g[8],g[1]),min(g[9],g[1])
            elif value != 0:
                bus,vg = node_bus(rows,gens)
                if cat in FIXED:
                    pmax,pmin = value,value
                elif cat in VARIABLE:
                    pmax,pmin = max(value,0.0),min(value,0.0)
                else:
                    pmax,pmin = max(float(capacity.get(node,0.0)),value),min(value,0.0)
                index = case.add_row("gen",{"bus":bus,"Pg":value,"Qmax":0.0,"Qmin":0.0,
                    "Vg":vg,"mBase":case.baseMVA,"status":1,"Pmax":pmax,"Pmin":pmin})
                case.tables["gencost"][index] = [2,0.0,0.0,3,",".join(f"{x:g}" for x in costs[cat])]
                gencat.insert(index,cat)
                added.append((cat,node,bus,value))
    after = tally()

    # foreign generation
    for node,folder in FOREIGN.items():
        dispatch = hour(os.path.join(HERE,folder),f"{node}.csv",timestamp)["dispatch_MW"]
        rows = nodes[node]
        busset = {b[0] for b in rows}
        members = [g for g,c in zip(gens,gencat) if g[0] in busset and c is not None]
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
            added.append(("foreign",node,bus[0],dispatch))

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
        bus,vg = node_bus(nodes[node],gens)
        index = case.add_row("gen",{"bus":bus,"Pg":value,"Qmax":qmax,"Qmin":-qmax,
            "Vg":vg,"mBase":case.baseMVA,"status":1,"Pmax":pmax,"Pmin":pmin})
        case.tables["gencost"][index] = [2,0.0,0.0,3,"0,0,0"]
        gencat.insert(index,"battery_storage")
        storage.append((node,bus,pmin,pmax,qmax,value,"no report" if pd.isna(net) else ""))

    result = case.solve("pf")
    if not result["success"]:
        raise ValueError("power flow failed")
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
    print(f"wrote wecc240/wecc240_2020.py at {timestamp}: {case.size()}")
    print(f"  load {sum(b[2] for b in buses):.0f} MW at {len(load)} nodes; "
        f"buses set to no load: {unloaded}")
    print(f"  generation {sum(g[1] for g in gens):.0f} MW scheduled, slack picked up {slack:.0f} MW, "
        f"losses {result['losses_MW']:.0f} MW")
    print("  US generation by category, MW (2018 case -> data):")
    for cat in CATEGORIES:
        print(f"    {cat:16s} {before[cat]:9.1f} -> {after[cat]:9.1f}")
    print(f"  {len(added)} generators added:")
    for cat,node,bus,value in added:
        print(f"    {cat:16s} node {node} bus {bus}: {value:.1f} MW")
    print(f"  {len(storage)} battery storage generators added "
        f"({sum(x[3] for x in storage):.1f} MW discharge, {-sum(x[2] for x in storage):.1f} MW charge, "
        f"{sum(x[5] for x in storage):.1f} MW scheduled):")
    for node,bus,pmin,pmax,qmax,value,note in storage:
        print(f"    node {node} bus {bus}: P {pmin:.1f}..{pmax:.1f} MW, Q +/-{qmax:.1f} MVAr, "
            f"Pg {value:.2f} MW {note}".rstrip())
    print(f"  power flow: Vm {vmin:.3f}-{vmax:.3f} pu, buses outside Vmin-Vmax: {outside}; "
        f"{overloaded} branches above rateA")

if __name__ == "__main__":
    main()
