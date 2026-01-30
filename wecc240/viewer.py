import marimo

__generated_with = "0.19.7"
app = marimo.App(width="full")


@app.cell
def _(mo):
    mo.md(r"""
    # WECC 240 Load Data for 2020

    Choose the node to view. Note that nodes with no loads are not listed.
    """)
    return


@app.cell
def _(pd):
    nodes = pd.read_csv("gis/wecc240.csv",index_col="GEOHASH").NAME.to_dict()
    return (nodes,)


@app.cell
def _(loads_GW, mo, nodes):
    load_ui = mo.ui.dropdown(
        label="Node:",
        options={f"{nodes[x]} ({x})":x for x in loads_GW.columns if loads_GW[x].abs().sum() > 0})
    load_ui
    return (load_ui,)


@app.cell
def _(pd):
    loads_GW = pd.read_csv("wecc240_2020_load.csv",index_col="timestamp",parse_dates=["timestamp"])*1e-3
    return (loads_GW,)


@app.cell
def _(loads_GW):
    total_load_GW = loads_GW.sum(axis=1).to_frame()
    total_load_GW.columns=["REGROW Load Model"]
    return (total_load_GW,)


@app.cell
def _(load_ui, loads_GW, mo, plt, total_load_GW):
    _figsize=(10,7)
    if load_ui.value is None:
        total_load_GW.iloc[12:].plot(figsize=_figsize)

        # see https://wecc-spdp-weccgeo.hub.arcgis.com/datasets/404f2439b7ff41b382e3792ac011003d/explore
        plt.axhline(163.456,label="WECC Reported Peak",color="k",linestyle=":")
    
    else:
        loads_GW[load_ui.value].iloc[12:].plot(figsize=_figsize)

    plt.title("WECC 240 2020")
    plt.xlabel("Date/Time")
    plt.ylabel("Power (GW)")
    plt.grid()
    plt.legend()

    mo.mpl.interactive(plt.gcf())
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import matplotlib.pyplot as plt
    return mo, pd, plt


if __name__ == "__main__":
    app.run()
