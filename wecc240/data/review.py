import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _(pd):
    node_dg = pd.read_csv("wecc240_dg.csv.gz",index_col=[0],parse_dates=[0])/1000
    node_mw = pd.read_csv("wecc240_load.csv.gz",index_col=[0],parse_dates=[0])
    node_gis = pd.read_csv("wecc240.csv",index_col=[0])
    return node_dg, node_gis, node_mw


@app.cell
def _(mo, node_gis, node_mw):
    # node dropdown
    _options = node_mw.columns
    _nodename = {y: f"{x} ({y})" for x, y in node_gis[["NAME", "GEOHASH"]].values}
    node_ui = mo.ui.dropdown(
        options={_nodename[x]: x for x in _options},
        label="Node:",
    )
    return (node_ui,)


@app.cell
def _(dt, mo, node_mw):
    # date range
    date_ui = mo.ui.date_range(start=min(node_mw.index).date(),stop=max(node_mw.index).date(),value=(dt.date(2020,8,14),dt.date(2020,8,21)))
    return (date_ui,)


@app.cell
def _(date_ui, pd):
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")
    return (date_range,)


@app.cell
def _(date_range, node_dg, node_mw, node_ui):
    _options = dict(grid=True,figsize=(10,7),ylabel="GW",title="Load")
    _mw = node_mw.loc[date_range]
    _dg = node_dg.loc[date_range]
    if node_ui.value is None:
        timeseries = (_mw.sum(axis=1)/1000).plot()
        _netload = (_mw - _dg).sum(axis=1)/1000
    else:
        timeseries = (_mw[node_ui.value]/1000).plot()
        _netload = (_mw[node_ui.value] - _dg[node_ui.value])/1000
    _netload.plot(ax=timeseries,**_options)
    timeseries.legend(["Total load", "Net load"])
    None
    return (timeseries,)


@app.cell
def _(date_ui, mo, node_ui, timeseries):
    mo.ui.tabs({
        "Timeseries": mo.vstack([
            mo.hstack([node_ui,date_ui],justify='start'),mo.mpl.interactive(timeseries)]),
        "Map": None
    })
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import datetime as dt

    return dt, mo, pd


if __name__ == "__main__":
    app.run()
