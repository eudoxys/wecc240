import marimo

__generated_with = "0.19.6"
app = marimo.App(width="full")


@app.cell
def _(mo):
    mo.md(r"""
    # WECC 240 2025 Model Data
    """)
    return


@app.cell
def _(mo):
    data_ui = mo.ui.radio(options=["Load","Generation","Solar","Wind","DG"],label="Data:",inline=True,value="Load")
    data_ui
    return (data_ui,)


@app.cell
def _(pd):
    nodes = pd.read_csv("gis/wecc240.csv",index_col="GEOHASH").NAME.to_dict()
    return (nodes,)


@app.cell
def _(data_GW, mo, nodes):
    node_ui = mo.ui.dropdown(
        label="Node:",
        options={f"{nodes[x]} ({x})":x for x in data_GW.columns if data_GW[x].abs().sum() > 0})
    node_ui
    return (node_ui,)


@app.cell
def _(data_ui, mo, os, pd):
    _file = f"wecc240_2025_{data_ui.value.lower()}.csv"
    mo.stop(not os.path.exists(_file),mo.md(f"**<font color=red>ERROR**: <code>{_file}</code> does not exist</font>"))
    data_GW = pd.read_csv(_file,index_col="timestamp",parse_dates=["timestamp"])*1e-3
    return (data_GW,)


@app.cell
def _(data_GW):
    total_GW = data_GW.sum(axis=1).to_frame()
    total_GW.columns=["REGROW Load Model"]
    return (total_GW,)


@app.cell
def _(data_GW, mo, node_ui, plt, total_GW):
    figsize = (10, 7)
    if node_ui.value is None:
        total_GW.plot(figsize=figsize)

        # see https://wecc-spdp-weccgeo.hub.arcgis.com/datasets/404f2439b7ff41b382e3792ac011003d/explore
        plt.axhline(163.456, label="WECC Reported Peak", color="k", linestyle=":")

    else:
        data_GW[node_ui.value].plot(figsize=figsize)

    plt.title(node_ui.selected_key)
    plt.xlabel("Date/Time")
    plt.ylabel("Power (GW)")
    plt.grid()
    plt.legend()
    hourly = mo.mpl.interactive(plt.gcf())
    return figsize, hourly


@app.cell
def _(data_GW, figsize, node_ui, total_GW):
    if node_ui.value is None:
        _data = total_GW
    else:
        _data = data_GW[node_ui.value]
    monthly = _data.groupby(_data.index.month).mean().plot(
        figsize=figsize,
        grid=True,
        kind="bar",
        title=node_ui.selected_key,
        xlabel="Month of 2020",
        ylabel="Monthly average load (GW)",
    )
    return (monthly,)


@app.cell
def _(data_GW, hourly, mo, monthly):
    mo.ui.tabs({
        "Hourly":hourly,
        "Monthly":monthly,
        "Data":mo.ui.table(data_GW.round(3),
                           selection=None,
                           page_size=24,
                          ),
    })
    return


@app.cell
def _():
    import os
    import marimo as mo
    import pandas as pd
    import matplotlib.pyplot as plt
    return mo, os, pd, plt


if __name__ == "__main__":
    app.run()
