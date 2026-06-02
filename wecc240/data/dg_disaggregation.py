import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook disaggregates node DG to counties.
    """)
    return


@app.cell
def _(dt, mo):
    date_ui = mo.ui.date_range(
        label="Date range:",
        start="2018-01-01",
        stop="2022-12-31",
        value=(dt.date(2020, 8, 14), dt.date(2020, 8, 21)),
    )
    return (date_ui,)


@app.cell
def _(date_ui, pd):
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")
    return (date_range,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Load and DG data
    """)
    return


@app.cell
def _(mo, pd):
    with mo.status.spinner("Reading county load and node DG data"):
        county_mw = pd.read_csv("county_mw.csv.gz",index_col=[0],parse_dates=[0])
        node_dg = (pd.read_csv("wecc240_dg.csv.gz",index_col=[0],parse_dates=[0])/1000).round(3)
    return county_mw, node_dg


@app.cell
def _(county_mw, date_range, mo, node_dg):
    mo.accordion({
        "`county_mw` (county total load data)": county_mw.loc[date_range].round(3),
        "`node_dg` (node DG data)": node_dg.loc[date_range].round(3),
    },multiple=True)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## WECC model data
    """)
    return


@app.cell
def _(Counties, mo, pd):
    def county_st(x):
        return [f"{x} {y}" for x, y in x[["COUNTY", "ST"]].values]


    counties = Counties(
        use_index=["SYSTEM"], selection=["WECC"], set_index=["GEOHASH"]
    ).sort_values(["ST", "COUNTY"])
    wecc_counties = county_st(counties)
    wecc_gis = pd.read_csv(
        "../gis/wecc240.csv", index_col=["GEOHASH"], converters={"COUNTY": str}
    )
    caiso_counties = county_st(counties.set_index("REGION").loc["CAISO"])
    mo.accordion(
        {
            "`counties` (WECC counties data)": counties,
            "`wecc_counties` (list of WECC county names)": wecc_counties,
            "`wecc_gis` (WECC model GIS data)": wecc_gis,
            "`caiso_counties` (list of counties in CAISO)": caiso_counties,
        },multiple=True)
    return caiso_counties, counties, wecc_counties, wecc_gis


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Node mapping to counties
    """)
    return


@app.cell
def _(counties, mo, nearest, wecc_gis):
    with mo.status.spinner("Mapping nodes to counties"):

        load_nodes = wecc_gis[wecc_gis["LOAD"]>0].sort_index()[["BUS_I","NAME","LOAD","LAT","LON"]]
        node_map = {n:" ".join(nearest(x,counties)[["COUNTY","ST"]].values) for n,x in load_nodes.iterrows()}

    mo.accordion({
        "`load_nodes` (load node data)": load_nodes.sort_index(),
        "`node_map` (mapping of nodes to counties)": node_map,
    },multiple=True)
    return (node_map,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## County DG and net load results
    """)
    return


@app.cell
def _(county_mw, date_range, mo, node_dg, node_map, pd):
    with mo.status.spinner("Generating county DG and net load"):
        county_dg = pd.DataFrame(
            data={x:[0]*len(date_range) for x in county_mw.columns},
            index=date_range
        )
    
        for _node,_county in [(x,y) for x,y in node_map.items() if x in node_dg.columns]:
            county_dg[_county] += node_dg[_node]

        county_net = county_mw - county_dg

    mo.accordion({
        "`county_dg` (county DG data)": county_dg.loc[date_range].round(3),
        "`county_net` (county net load)": county_net.loc[date_range].round(3),
    },multiple=True)
    return county_dg, county_net


@app.cell
def _(mo):
    caiso_ui = mo.ui.checkbox(label="Plot CAISO only")
    return (caiso_ui,)


@app.cell
def _(caiso_ui, date_ui, mo):
    mo.hstack([date_ui,caiso_ui],justify='start')
    return


@app.cell
def _(
    caiso_counties,
    caiso_ui,
    county_mw,
    county_net,
    date_range,
    mo,
    wecc_counties,
):
    _options = dict(grid=True,figsize=(10,7),title=f"{'CAISO' if caiso_ui.value else 'WECC'} County loads")
    _counties = caiso_counties if caiso_ui.value else wecc_counties
    _ax = county_mw.loc[date_range][_counties].sum(axis=1).plot()
    county_net.loc[date_range][_counties].sum(axis=1).plot(ax=_ax,**_options)
    _ax.legend(["Total load","Net Load"])
    mo.mpl.interactive(_ax)
    return


@app.cell
def _(county_dg):
    county_dg.to_csv("county_dg.csv.gz",index=True,compression="gzip")
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import datetime as dt
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
