import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook aggregate bus load and dg up to node net load as follows:
    """)
    return


@app.cell
def _(mo):
    mo.mermaid("""
    flowchart LR
        **data/bus_dg.csv.gz** --> bus_dg
        **data/bus_mw.csv.gz** --> bus_mw
        subgraph Step 1: Calculate net bus load
            bus_dg --> sum
            bus_mw --> sum
            sum((+)) --> bus_net
        end
    
        bus_net --> **bus_net.csv.gz**
        bus_net --> grouper

        subgraph Step 2: Aggregate busses to nodes
            grouper([groupby.geohash.sum])
        end
    
        **gis/wecc240.csv** -----> grouper --> **data/node_net.csv**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Step 1: Calculate net bus load
    """)
    return


@app.cell
def _(mo, pd):
    with mo.status.spinner("Reading `bus_dg.csv.gz`..."):
        bus_dg = pd.read_csv("bus_dg.csv.gz",index_col=[0],parse_dates=[0])
    return (bus_dg,)


@app.cell
def _(mo, pd):
    with mo.status.spinner("Reading `bus_mw.csv.gz`..."):
        bus_mw = pd.read_csv("bus_mw.csv.gz",index_col=[0],parse_dates=[0])
    return (bus_mw,)


@app.cell
def _(bus_dg, bus_mw, mo):
    with mo.status.spinner("Calculating `bus_net`"):
        bus_net = bus_mw - bus_dg
    return (bus_net,)


@app.cell
def _(bus_dg, bus_mw, bus_net, mo):
    mo.accordion({
        "bus_dg": mo.ui.table(bus_dg.round(3),page_size=24,selection=None),
        "bus_mw": mo.ui.table(bus_mw.round(3),page_size=24,selection=None),
        "bus_net": mo.ui.table(bus_net.round(3),page_size=24,selection=None),
    },multiple=True)
    return


@app.cell
def _(bus_net, mo):
    def _save(*args,**kwargs):
        with mo.status.spinner("Saving `bus_net` to `bus_net.csv.gz`"):
            bus_net.round(3).to_csv("bus_net.csv.gz",index=True,header=True,compression="gzip")

    _save_ui = mo.ui.button(label="Save `bus_net` to `bus_net.csv.gz`",on_click=_save)
    _save_ui
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Step 2: Aggregate Busses to Nodes
    """)
    return


@app.cell
def _(mo, pd):
    with mo.status.spinner("Reading `../gis/wecc240.csv`..."):
        gis = pd.read_csv("../gis/wecc240.csv",usecols=["BUS_I","GEOHASH"])
    return (gis,)


@app.cell
def _(bus_net, gis, mo, pd):
    with mo.status.spinner("Calculating `node_net`..."):
        _nodelist = list(gis.GEOHASH.unique())
        node_net = pd.DataFrame(
            {x:[0]*len(bus_net.index) for x in _nodelist},
            index=bus_net.index,
            )
        for _bus,_node in [(str(x),y) for x,y in gis.values if str(x) in bus_net.columns]:
            node_net[_node] += bus_net[_bus].fillna(0)
    return (node_net,)


@app.cell
def _(gis, mo, node_net):
    mo.accordion({
        "gis": mo.ui.table(gis,selection=None),
        "node_net": mo.ui.table(node_net.round(3),selection=None,page_size=24)
    },multiple=True)
    return


@app.cell
def _(mo, node_net):
    def _save(*args,**kwargs):
        with mo.status.spinner("Saving `node_net` to `node_net.csv.gz`"):
            node_net.round(3).to_csv("node_net.csv.gz",index=True,header=True,compression="gzip")

    _save_ui = mo.ui.button(label="Save `node_net` to `node_net.csv.gz`",on_click=_save)
    _save_ui
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    return mo, pd


if __name__ == "__main__":
    app.run()
