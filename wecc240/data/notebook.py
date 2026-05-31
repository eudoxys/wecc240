import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook calculates the load at each node, not including DG.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Data flow
    """)
    return


@app.cell
def _(mo):
    with open("README.md","r") as fh:
        _graph = mo.mermaid(fh.read())
    _graph
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Procedure
    """)
    return


@app.cell
def _(Total, pd):
    # Settings

    # years for which mapping data is obtained
    start = 2018
    stop = 2022

    # pandas output display options
    # pd.options.display.max_columns = None
    pd.options.display.width = None
    # pd.options.display.max_rows = None
    show_rows = 240 # maximum table rows to display (long dataframes only)

    # hour, month, and year date ranges
    hour_range = pd.date_range(
        start=f"{start}-01-01 00:00:00+0000",
        end=f"{stop}-12-31 23:59:59+0000",
        freq="1h",
        )
    month_range = pd.date_range(
        start=f"{start}-01-01 00:00:00+0000",
        end=f"{stop}-12-31 23:59:59+0000",
        freq="MS",
        )
    year_range = pd.date_range(
        start=f"{start}-01-01 00:00:00+0000",
        end=f"{stop}-12-31 23:59:59+0000",
        freq="YS",
        )

    # disable total energy cache (saves memory)
    Total.cache = None
    return hour_range, month_range, show_rows, year_range


@app.cell(hide_code=True)
def _(mo, wecc_counties, wecc_states):
    mo.md(rf"""
    There are {len(wecc_counties)} counties in WECC's {len(wecc_states)} states.
    """)
    return


@app.cell
def _(Counties):
    # WECC counties and states
    wecc_counties = Counties(use_index=["SYSTEM"],selection=["WECC"],set_index=["GEOHASH"]).sort_values(["ST","COUNTY"])
    wecc_states = sorted(wecc_counties["ST"].unique())
    return wecc_counties, wecc_states


@app.cell(hide_code=True)
def _(mo, wecc_gis):
    mo.md(rf"""
    The WECC GIS data describes {len(wecc_gis)} busses.
    """)
    return


@app.cell
def _(mo, pd):
    # Read WECC bus gis data
    with mo.status.spinner("Loading WECC GIS data"):
        wecc_gis = pd.read_csv("../gis/wecc240.csv",
            index_col=["GEOHASH"],
            usecols=["GEOHASH","BUS_I","NAME","GEN","LOAD","LAT","LON"],
            converters={"COUNTY":str},
            ).rename({"LOAD":"BUS_LOAD_GW","GEN":"BUS_GEN_GW"},axis=1)
    return (wecc_gis,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 1: Aggregate the simulated county load (`county_mw`) stored in the file `county_mw.csv.gz` to monthly energy consumption (`county_mwh`).
    """)
    return


@app.cell
def _(Total, county_st, hour_range, mo, os, pd, show_rows, wecc_counties):
    # Aggregate county hourly total loads into monthly total energy
    with mo.status.spinner("Reading county loads") :
        if os.path.exists("county_mw.csv.gz"):
            county_mw = pd.read_csv("county_mw.csv.gz",index_col=[0],parse_dates=[0])
        else:
            county_mw = []
            for _state,_county in wecc_counties.sort_values(["ST","COUNTY"])[["ST","COUNTY"]].values:
                _county_st = f"{_county} {_state}"
                print(_county_st,end="...",flush=True)
                county_mw.append(Total(_state,_county,date_range=hour_range,samples=0)["elec_total_MW"].to_frame(county_st))
                print("ok")
            county_mw = pd.concat(county_mw,axis=1).round(3)
            county_mw.to_csv("county_mw.csv.gz")
        county_mwh = county_mw.resample("MS").sum()
    mo.accordion({
        "Table 1(a): `county_mw`":county_mw.iloc[:show_rows].round(3), 
        "Table 1(b): `county_mwh`":county_mwh.round(1),
    })
    return county_mw, county_mwh


@app.cell(hide_code=True)
def _(load_bus, load_nodes, mo):
    mo.md(rf"""
    Step 2: Identify the load nodes as the {len(load_bus)} busses (`load_bus`) that have non-zero power demand. These are aggregated into the {len(load_nodes)} load nodes (`load_nodes`) that have distributed generation data provisioned.
    """)
    return


@app.cell
def _(mo, nodedg_mw, pd, wecc_gis):
    # Aggregate counties to load nodes
    with mo.status.spinner("Aggregating loads to nodes"):

        # Collect busses with non-zero loads
        load_bus = wecc_gis[wecc_gis["BUS_LOAD_GW"]>0].sort_index()[["BUS_I","NAME","BUS_LOAD_GW"]]

        # Aggregate bus loads by node
        load_nodes = load_bus["BUS_LOAD_GW"].groupby("GEOHASH").sum().to_frame("NODE_LOAD_GW").sort_index()

        # Merge bus loads with bus nodes 
        _nodes = sorted(set(wecc_gis.index) & set(nodedg_mw.columns))
        load_bus = pd.merge(load_bus,load_nodes,left_index=True,right_index=True).loc[_nodes]

        # Compute contribution factors of bus loads to node loads
        load_bus["LOAD_CF"] = load_bus["BUS_LOAD_GW"] / load_bus["NODE_LOAD_GW"]
    mo.accordion({
        "Table 2(a): `load_bus`": load_bus,
        "Table 2(b): `load_nodes`": load_nodes,
    })
    return load_bus, load_nodes


@app.cell(hide_code=True)
def _(mo):
    mo.md(rf"""
    Step 3: Map the counties to the nearest load nodes (`county_node`).
    """)
    return


@app.cell
def _(load_bus, mo, nearest2, pd, wecc_counties, wecc_gis):
    # Map counties to nodes
    def nearest(bus, nodes):
        """Find nearest node to a bus"""
        ix, ll, dist = nearest2((bus.LAT, bus.LON), nodes[["LAT", "LON"]].values)
        return nodes.iloc[ix]


    # find the nearest load and gen nodes for each county
    with mo.status.spinner("Mapping counties to load busses"):
        county_node = {
            n: nearest(
                x,
                pd.merge(
                    load_bus,
                    wecc_gis[["LAT", "LON"]],
                    left_index=True,
                    right_index=True,
                ),
            ).name
            for n, x in wecc_counties.iterrows()
        }
        county_node = pd.DataFrame(
            data={"node": county_node.values(), "county": county_node.keys()}
        ).set_index("county")
        county_node["county_st"] = [f"{x} {y}" for x,y in wecc_counties.loc[county_node.index][["COUNTY","ST"]].values]
        county_node["state"] = wecc_counties.loc[county_node.index]["ST"]
        county_node.to_csv("county_node.csv",index=True)
    mo.accordion({
        "Table 3: `county_node`": county_node.sort_index(),
    })
    return (county_node,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(rf"""
    Step 4: Aggregate the simulated county loads to the node hourly power demand (`node_mw`) and the node monthly energy consumption (`node_mwh`)
    """)
    return


@app.cell
def _(county_mw, county_node, hour_range, mo, pd, show_rows, wecc_counties):
    # Aggregate counties to nodes and aggregate monthly energy
    with mo.status.spinner("Aggregating simulated county loads to node hourly and monthly energy"):
        node_mw = []
        for _node in sorted(county_node["node"].unique()):
            node_mw.append(pd.DataFrame(
                data={_node:[0]*len(hour_range)},
                index=hour_range,
            ))
        node_mw = pd.concat(node_mw,axis=1)
        for _geohash,_state,_county in wecc_counties.sort_values(["ST","COUNTY"])[["ST","COUNTY"]].reset_index().values:
            _county_st = f"{_county} {_state}"
            _node = county_node.loc[_geohash]["node"]
            node_mw[_node] += county_mw[_county_st]
        node_mwh = node_mw.resample("MS").sum()
    mo.accordion({
        "Table 4(a): `node_mw`": node_mw.iloc[:show_rows].round(3),
        "Table 4(b): `node_mwh`": node_mwh.round(1),
    })
    return node_mw, node_mwh


@app.cell(hide_code=True)
def _(mo):
    mo.md(rf"""
    Step 5: Calculate each county's contribution factor (`county_cf`) to each node.
    """)
    return


@app.cell
def _(county_mwh, county_node, mo, node_mwh):
    # Calculate county contribution factors to nodes
    with mo.status.spinner("Calculating county contribution factors to nodes"):
        county_cf = county_mwh.copy()
        # for _geohash,_state,_county in wecc_counties.sort_values(["ST","COUNTY"])[["ST","COUNTY"]].reset_index().values:
        # _county_st = f"{_county} {_state}"
        for _geohash, _data in county_node.iterrows():
            county_cf[_data["county_st"]] /= node_mwh[_data["node"]]
    mo.accordion(
        {
            "Table 5: `county_cf`": county_cf.round(4),
        }
    )
    return (county_cf,)


@app.cell
def _(county_cf, county_node, np):
    # Check node to county energy mapping (should all sum to 1)
    node_county = county_node.reset_index().set_index("node")
    for _counties in node_county.groupby("node")["county_st"].apply(list):
        if not np.allclose(county_cf[_counties].sum(axis=1).values,1.0):
            raise RuntimeError(f"ERROR: county_cf checksum failed for counties {_counties}:")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(rf"""
    Step 6: Read the node hourly DG power generation (`nodedg_mw`) and compute the monthly DG energy production (`nodedg_mwh`).
    """)
    return


@app.cell
def _(mo, pd, show_rows):
    # Read DG data
    with mo.status.spinner("Reading the simulated node DG"):
        nodedg_mw = pd.read_csv("wecc240_dg.csv.gz",index_col=[0],parse_dates=[0])/1000
        nodedg_mwh = nodedg_mw.resample("MS").sum()
    mo.accordion({
        "Table 6(a): `nodedg_mw`": nodedg_mw.iloc[:show_rows].round(3),
        "Table 6(b): `nodedg_mwh`": nodedg_mwh.round(1),
    })
    return (nodedg_mw,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 7: Add node hourly DG power (`nodedg_mw`) to simulated node hourly demand (`node_mw`) to generate hourly node demand power (`nodeld_mw`) and monthly node energy consumption (`nodeld_mwh`)
    """)
    return


@app.cell
def _(mo, node_mw, nodedg_mw, show_rows):
    with mo.status.spinner("Calculating node hourly demand power and monthly energy"):
        nodeld_mw = (node_mw + nodedg_mw)[node_mw.columns]
        nodeld_mwh = nodeld_mw.resample("MS").sum()
    mo.accordion({
        "Table 7(a): `nodeld_mw`": nodeld_mw.iloc[:show_rows].round(3),
        "Table 7(b): `nodeld_mwh`": nodeld_mwh.round(1),
    })
    return (nodeld_mw,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 8: Disaggregate hourly node load into hourly county hourly load and DG (`countyld_mw` and `countydg_mw`) and monthly energy consumption and production (`countyld_mwh`)
    """)
    return


@app.cell
def _(county_cf, county_node, mo, nodedg_mw, nodeld_mw, pd, show_rows):
    with mo.status.spinner("Disaggregating node load and DG to county load and DG"):
        countyld_mw = []
        countydg_mw = []
        cf = county_cf.resample("1h").ffill()
        for _county,_data in county_node.set_index("county_st")[["node"]].iterrows():
            countyld_mw.append(pd.DataFrame(
                data={_county:nodeld_mw[_data["node"]] * cf[_county]},
                index=nodeld_mw.index,
            ))
            countydg_mw.append(pd.DataFrame(
                data={_county:nodedg_mw[_data["node"]] * cf[_county]},
                index=nodeld_mw.index,
            ))
        countyld_mw = pd.concat(countyld_mw,axis=1)
        countydg_mw = pd.concat(countydg_mw,axis=1)
        countyld_mwh = countyld_mw.resample("MS").sum()
        countydg_mwh = countydg_mw.resample("MS").sum()
    mo.accordion({
        "Table 8(a): `countyld_mw`": countyld_mw.iloc[:show_rows].round(3),
        "Table 8(b): `countyld_mwh`": countyld_mwh.round(1),
        "Table 8(c): `countydg_mw`": countydg_mw.iloc[:show_rows].round(3),
        "Table 8(d): `countydg_mwh`": countydg_mwh.round(1),
    })
    return countydg_mw, countyld_mw


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 9: Aggregate hourly county load and DG (`countyld_mw` and `countydg_mw) to state hourly load and DG (`stateld_mw` and `statedg_mw) and compute the monthly state energy consumption and production (`stateld_mwh` and `statedg_mwh`)
    """)
    return


@app.cell
def _(countydg_mw, countyld_mw, hour_range, mo, pd, show_rows, wecc_states):
    with mo.status.spinner("Aggregating hourly county load and DG and monthly county energy consumption and production"):
        stateld_mw = pd.DataFrame(
            data={x:[0]*len(hour_range) for x in wecc_states},
            index=hour_range
        )
        statedg_mw = pd.DataFrame(
            data={x:[0]*len(hour_range) for x in wecc_states},
            index=hour_range
        )
        for _county in countyld_mw.columns:
            _state = _county.split()[-1]
            stateld_mw[_state] += countyld_mw[_county]
            statedg_mw[_state] += countydg_mw[_county]
        stateld_mwh = stateld_mw.resample("MS").sum()
        statedg_mwh = statedg_mw.resample("MS").sum()
    mo.accordion({
        "Table 9(a): `stateld_mw`": stateld_mw.iloc[:show_rows].round(3),
        "Table 9(b): `stateld_mwh`": stateld_mwh.round(1),
        "Table 9(c): `statedg_mw`": statedg_mw.iloc[:show_rows].round(3),
        "Table 9(d): `statedg_mwh`": statedg_mwh.round(1),
    })
    return (statedg_mwh,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 10: Read the monthly state energy consumption (`state_mwh`) from EIA and compute state energy demand (`demand_mwh`)
    """)
    return


@app.cell
def _(Energy, mo, pd, statedg_mwh, wecc_states, year_range):
    # Read monthly energy usage from EIA
    with mo.status.spinner("Read monthly state energy"):
        state_mwh = []
        for _state in wecc_states:
            _mwh = Energy(_state,None,[min(year_range).year,max(year_range).year])
            state_mwh.append(_mwh.sum(axis=1).to_frame(_state))
        state_mwh = pd.concat(state_mwh,axis=1)
    demand_mwh = state_mwh + statedg_mwh
    mo.accordion({
        "Table 10(a): `state_mwh`": state_mwh.round(1),
        "Table 10(b): `demand_mwh`": demand_mwh.round(1)    ,
    })
    return (demand_mwh,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 11: Compute state monthly simulated energy consumption (`total_mwh`) from county monthly simulated energy consumption (`county_mwh`)
    """)
    return


@app.cell
def _(county_mwh, county_node, demand_mwh, mo, month_range, pd):
    with mo.status.spinner("C"):
        total_mwh = pd.DataFrame(
            data={x:[0]*len(month_range) for x in demand_mwh.columns},
            index=month_range,
        )
        for _geohash,_data in county_node.iterrows():
            total_mwh[_data["state"]] += county_mwh[_data["county_st"]]
    mo.accordion({"Table 11: `total_mwh`": total_mwh.round(1)})
    return (total_mwh,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 12: Compute the state monthly energy calibration factors (`state_calibration`)
    """)
    return


@app.cell
def _(demand_mwh, mo, total_mwh):
    state_calibration = demand_mwh / total_mwh
    mo.accordion({"Table 12: state_calibration": state_calibration.round(4)})
    return (state_calibration,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Step 13: Compute the calibrated county power demand (`actual_mw`)
    """)
    return


@app.cell
def _(county_mw, mo, pd, show_rows, state_calibration):
    with mo.status.spinner("Recalibrating county hourly power demand"):
        actual_mw = []
        _calibration = state_calibration.resample("1h").ffill()
        for _county in county_mw.columns:
            _state = _county.split()[-1]
            actual_mw.append((county_mw[_county] * _calibration[_state]).to_frame(_county))
        actual_mw = pd.concat(actual_mw,axis=1)
    mo.accordion({
        "Table 13: `actual_mw`": actual_mw.iloc[:show_rows],
    })
    return (actual_mw,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Table 14: Reaggregate calibrated county power demand (`actual_mw`) to final node power demand (`final_mw`)
    """)
    return


@app.cell
def _(
    actual_mw,
    county_node,
    hour_range,
    mo,
    node_mw,
    pd,
    show_rows,
    wecc_counties,
):
    # Aggregate calibrated county power demand to calibrated node power demand
    with mo.status.spinner("Aggregating calibrated county loads to final node demand"):
        final_mw = []
        for _node in sorted(county_node["node"].unique()):
            final_mw.append(pd.DataFrame(
                data={_node:[0]*len(hour_range)},
                index=hour_range,
            ))
        final_mw = pd.concat(final_mw,axis=1)
        for _geohash,_state,_county in wecc_counties.sort_values(["ST","COUNTY"])[["ST","COUNTY"]].reset_index().values:
            _county_st = f"{_county} {_state}"
            _node = county_node.loc[_geohash]["node"]
            final_mw[_node] += actual_mw[_county_st]
        final_mw.round(3).to_csv("wecc240_load.csv.gz",index=True)
    mo.accordion({
        "Table 14: `final_mw`": node_mw.iloc[:show_rows].round(3),
    })
    return


@app.cell
def _():
    import marimo as mo

    import os
    from time import time

    import pandas as pd
    import numpy as np
    import scipy as sp

    from loads import Total, Energy, DG
    from loads.dgen import compile
    from fips import Counties
    from geohash import nearest2
    from eia import HS861m, Form860m, Form861m


    return Counties, Energy, Total, mo, nearest2, np, os, pd


if __name__ == "__main__":
    app.run()
