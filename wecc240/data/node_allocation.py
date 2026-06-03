import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook allocates county loads to nodes.
    """)
    return


@app.cell
def _(Counties, mo, pd):
    wecc_counties = (
        Counties(use_index="SYSTEM", selection="WECC")
        .sort_values(["ST", "COUNTY"])
        .reset_index(drop=True)
    )
    wecc_counties["COUNTY_ST"] = [
        f"{x} {y}" for x, y in wecc_counties[["COUNTY", "ST"]].values
    ]

    wecc_gis = pd.read_csv("../gis/wecc240.csv").rename(
        {"GEOHASH": "NODE"}, axis=1
    )

    load_nodes = wecc_gis[wecc_gis["LOAD"]>0]

    mo.accordion(
        {
            "wecc_counties": wecc_counties,
            "wecc_gis": wecc_gis,
            "load_nodes": load_nodes,
        },
        multiple=True,
    )
    return load_nodes, wecc_counties


@app.cell
def _(dt, mo):
    date_ui = mo.ui.date_range(
        label="Date range:",
        start="2018-01-01",
        stop="2022-12-31",
        value=(dt.date(2020, 8, 14), dt.date(2020, 8, 21)),
    )
    date_ui
    return (date_ui,)


@app.cell
def _(date_ui, pd):
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")
    return (date_range,)


@app.cell
def _(date_range, mo, pd):
    with mo.status.spinner("Loading county_total.csv.gz"):
        county_total = pd.read_csv("county_total.csv.gz",index_col=[0],parse_dates=[0])

    mo.accordion({
        "county_total": county_total.loc[date_range],
    },multiple=True)
    return (county_total,)


@app.cell
def _(county_total, date_range, load_nodes, mo, nearest, pd, wecc_counties):
    node_total = pd.DataFrame(
        data={x:[0]*len(date_range) for x in sorted(set(load_nodes["NODE"]))},
        index=date_range,
    )
    county_node = {
        nearest(x, wecc_counties)["COUNTY_ST"]: n
            for n, x in load_nodes.set_index("NODE").iterrows()
        }

    for _county,_node in county_node.items():
        node_total[_node] += county_total[_county]
    
    mo.accordion({
        "node_total": node_total,
        "county_node": county_node,
    },multiple=True)
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
