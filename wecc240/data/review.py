import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _(pd):
    node_dg = pd.read_csv("wecc240_dg.csv.gz",index_col=[0],parse_dates=[0])/1000
    node_mw = pd.read_csv("wecc240_load.csv.gz",index_col=[0],parse_dates=[0])
    node_gis = pd.read_csv("../gis/wecc240.csv",index_col=[0],converters={"COUNTY":str})
    return node_dg, node_gis, node_mw


@app.cell
def _(node_gis):
    from fips import Counties
    _weccfips=Counties(use_index="REGION",selection="CAISO").reset_index().set_index("FIPS").index.values.tolist()
    caiso = {
        "Node": node_gis[node_gis["COUNTY"].isin(_weccfips)],
        "BA": node_gis[node_gis["BA"]=="CA"],
    }
    return (caiso,)


@app.cell
def _(mo):
    caiso_ui = mo.ui.dropdown(label="CAISO by:",options=["Node","BA"],value="Node")
    return (caiso_ui,)


@app.cell
def _(caiso, caiso_ui, mo, node_gis, node_mw):
    # node dropdown
    _nodename = {y: f"{x} ({y})" for x, y in node_gis[["NAME", "GEOHASH"]].values}
    _options = {_nodename[x]: [x] for x in node_mw.columns}
    _options["WECC"] = node_mw.columns
    _options["CAISO"] = [x for x in caiso[caiso_ui.value]["GEOHASH"].unique().tolist() if x in node_mw.columns]
    node_ui = mo.ui.dropdown(
        options={x:_options[x] for x in sorted(_options)},
        label="Node:",
        value="CAISO",
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
    _options = dict(grid=True,figsize=(10,7),ylabel="GW",title="Load",xlabel="Date/Time (UTC)")
    _mw = node_mw.loc[date_range]
    _dg = node_dg.loc[date_range]
    _total = _mw[node_ui.value].sum(axis=1)/1000
    timeseries = _total.plot()
    peak_total = _total.max()
    _netload = (_mw[node_ui.value] - _dg[node_ui.value]).sum(axis=1)/1000
    peak_net = _netload.max()
    _netload.plot(ax=timeseries,**_options)
    timeseries.legend(["Total load", "Net load"])
    None
    return peak_net, peak_total, timeseries


@app.cell
def _(caiso_ui, date_ui, mo, node_ui, peak_net, peak_total, timeseries):
    mo.ui.tabs(
        {
            "Timeseries": mo.vstack(
                [
                    mo.hstack(
                        [
                            node_ui,
                            date_ui,
                            caiso_ui,
                            mo.md(
                                f"Peaks: Total={peak_total:.1f} GW, Net={peak_net:.1f} GW"
                            ),
                        ],
                        justify="start",
                    ),
                    mo.mpl.interactive(timeseries),
                ]
            ),
            "Map": None,
        }
    )
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import datetime as dt

    return dt, mo, pd


if __name__ == "__main__":
    app.run()
