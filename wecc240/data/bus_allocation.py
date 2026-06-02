import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook allocates
    the calibrated county loads to the WECC load busses.
    """)
    return


@app.cell
def _(Counties, mo, pd):
    def county_st(x):
        return {n: f"{x} {y}" for n, x, y in x[["FIPS", "COUNTY", "ST"]].values}


    wecc_counties = Counties(use_index=["SYSTEM"], selection=["WECC"]).sort_values(
        ["ST", "COUNTY"]
    )

    # map wecc_counties to loads
    fips2county_st = county_st(wecc_counties)
    wecc_counties["COUNTY_ST"] = fips2county_st.values()
    wecc_gis = pd.read_csv("../gis/wecc240.csv", converters={"COUNTY": str,"BUS_I": str})
    wecc_loads = (
        wecc_gis[(wecc_gis["LOAD"] > 0) & (wecc_gis["COUNTY"] != "")]
        .set_index("COUNTY")[["LOAD", "GEOHASH", "BUS_I","LAT","LON"]]
        .sort_index().rename({"GEOHASH":"NODE"},axis=1)
    )
    wecc_loads["COUNTY_ST"] = [fips2county_st[x] for x in wecc_loads.index]

    # compute totals
    _totals = wecc_loads.groupby("COUNTY").sum()["LOAD"].to_frame("TOTAL")
    wecc_loads = pd.merge(
        wecc_loads, _totals, left_index=True, right_index=True
    )
    wecc_loads["LOAD_CF"] = wecc_loads["LOAD"] / wecc_loads["TOTAL"]
    mo.accordion(
        {
            "wecc_counties": wecc_counties,
            # "fips2county_st": fips2county_st,
            "wecc_gis": wecc_gis,
            "wecc_loads": wecc_loads.round(4),
            # "_totals": _totals.round(4),
        },
        multiple=True,
    )
    return wecc_counties, wecc_loads


@app.cell(hide_code=True)
def _(mo, pd):
    with mo.status.spinner("Reading county total and DG data"):
        county_total = pd.read_csv("county_total.csv.gz",index_col=[0],parse_dates=[0])
        county_dg = pd.read_csv("county_dg.csv.gz",index_col=[0],parse_dates=[0])
    mo.accordion({
        "county_total": county_total.round(3),
        "county_dg": county_dg.round(3),
    })
    return county_dg, county_total


@app.cell(hide_code=True)
def _(county_total, dt, mo):
    date_ui = mo.ui.date_range(
        label="Date range:",
        start=min(county_total.index).date(),
        stop=max(county_total.index).date(),
        value=(dt.date(2020, 8, 14), dt.date(2020, 8, 21)),
    )
    return (date_ui,)


@app.cell(hide_code=True)
def _(date_ui):
    date_ui
    return


@app.cell(hide_code=True)
def _(date_ui, pd):
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")
    return (date_range,)


@app.cell
def _():
    return


@app.cell
def _(
    county_dg,
    county_total,
    date_range,
    mo,
    nearest,
    pd,
    wecc_counties,
    wecc_loads,
):
    with mo.status.spinner("Computing county load allocations to busses"):
        bus_total = pd.DataFrame(
            data={
                str(x): [0] * len(county_total.index)
                for x in sorted(wecc_loads["BUS_I"].unique())
            },
            index=county_total.index,
        ).rename_axis("timestamp")
        bus_dg = bus_total.copy()

        # map counties with busses
        _nodeloads = wecc_loads.reset_index().set_index("NODE")
        _countyloads = wecc_loads.reset_index().set_index("COUNTY_ST")
        _done = []
        for _node, _data in _nodeloads.iterrows():
            _cf = _data["LOAD_CF"]
            _bus = str(_data["BUS_I"])
            _county = _data["COUNTY_ST"]
            bus_total[_bus] += county_total[_county] * _cf
            bus_dg[_bus] += county_dg[_county] * _cf
            print(f"bus {_bus} ({_county}) <-- {_cf:.4f} * {county_total[_county].max():.3f}, total={bus_total[_bus].max():.3f}, dg={bus_dg[_bus].max():.3f}")
            _done.append(_county)

        # map counties with no busses to nearest node
        _map = {
            nearest(x, wecc_counties)["COUNTY_ST"]: n
            for n, x in _nodeloads.iterrows()
        }
        for _county in [x for x in sorted(set(wecc_counties["COUNTY_ST"])-set(_done)) if x in _map]:
            _node = _map[_county]
            for _, _data in _nodeloads.loc[[_node]].iterrows():
                _target = _data["COUNTY_ST"]
                _values = _countyloads.loc[_target,["BUS_I", "LOAD_CF"]].values.tolist()
                if not isinstance(_values[0],list): 
                    _values = [_values]
                for _bus, _cf in _values:
                    bus_total[_bus] += county_total[_county] * _cf
                    bus_dg[_bus] += county_dg[_county] * _cf
                    print(f"bus {_bus} ({_target}) <-- {_cf:.4f} * {county_total[_county].max():.3f} ({_county}), total={bus_total[_bus].max():.3f}, dg={bus_dg[_bus].max():.3f}")
    mo.accordion(
        {
            "bus_total": bus_total.loc[date_range].round(3),
            "bus_dg": bus_dg.loc[date_range].round(3),
        }
    )
    return bus_dg, bus_total


@app.cell
def _(bus_dg, bus_total, county_dg, county_total, date_range, mo):
    mo.md(f"""
    | Check | Counties | Busses |
    | ----- | -------- | ------ |
    | Total | {county_total.loc[date_range].sum(axis=1).max().round(1)/1000:.1f} GW | {bus_total.loc[date_range].sum(axis=1).max().round(1)/1000:.1f} GW|
    | DG | {county_dg.loc[date_range].sum(axis=1).max().round(1)/1000:.1f} GW | {bus_dg.loc[date_range].sum(axis=1).max().round(1)/1000:.1f} GW |
    """)
    return


@app.cell
def _():
    return


@app.cell
def _():
    import marimo as mo
    import datetime as dt
    import pandas as pd
    from fips import Counties
    from geohash import nearest2


    def nearest(location, locations):
        """Find nearest node to a bus"""
        ix, ll, dist = nearest2(
            (location.LAT, location.LON), locations[["LAT", "LON"]].values
        )
        return locations.iloc[ix]

    return Counties, dt, mo, nearest, pd


if __name__ == "__main__":
    app.run()
