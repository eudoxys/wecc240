import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This folder describes the notebooks used to prepare the model data used in simulations of the WECC 240 system. The data is shown in Figure 1.
    """)
    return


@app.cell
def _(mo):
    with open("README.md","r") as fh:
        _result = "\n".join(fh.read().split("```")[1].split("\n")[1:])
        print(_result)
    mo.mermaid(f"""
    ---
    title: Figure 1 - WECC 240 model data flow
    ---
    {_result}""")
    return


@app.cell
def _():
    from bus_gis import app as bus_gis_app
    from node_dg import app as node_dg_app
    from node_total import app as node_total_app
    from node_net import app as node_net_app

    return bus_gis_app, node_dg_app, node_net_app, node_total_app


@app.cell
async def _(bus_gis_app, mo, node_dg_app, node_net_app, node_total_app):
    bus_gis = await bus_gis_app.embed()
    node_dg = await node_dg_app.embed()
    node_total = await node_total_app.embed()
    node_net = await node_net_app.embed()
    mo.ui.tabs({
        "bus_gis": bus_gis.output,
        "node_total":node_total.output,
        "node_dg":node_dg.output,
        "node_net":node_net.output,
    },lazy=True)
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
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")[:-1]
    return (date_range,)


@app.cell
def _(bus_dg, mo):
    _pagewidth = 7
    get_busses_page, set_busses_page = mo.state(0)
    busses_pages = [
        f"{bus_dg.columns[x]}-{bus_dg.columns[min(x+_pagewidth,len(bus_dg.columns))-1]}"
        for x in range(0, len(bus_dg.columns), _pagewidth)
    ]
    busses_first = mo.ui.button(
        label="|&lt;",
        on_click=lambda x: set_busses_page(0),
    )
    busses_previous = mo.ui.button(
        label="&lt;",
        on_click=lambda x: set_busses_page(max(0, get_busses_page() - 1)),
    )
    busses_next = mo.ui.button(
        label="&gt;",
        on_click=lambda x: set_busses_page(
            min(get_busses_page() + 1, len(busses_pages) - 1)
        ),
    )
    busses_last = mo.ui.button(
        label="&gt;|",
        on_click=lambda x: set_busses_page(len(busses_pages) - 1),
    )
    return (
        busses_first,
        busses_last,
        busses_next,
        busses_pages,
        busses_previous,
        get_busses_page,
    )


@app.cell
def _(busses_pages, get_busses_page, mo):
    busses_select = mo.ui.dropdown(
        options=busses_pages, value=busses_pages[get_busses_page()]
    )
    return (busses_select,)


@app.cell
def _(
    busses_first,
    busses_last,
    busses_next,
    busses_previous,
    busses_select,
    mo,
):
    bus_ui = mo.hstack(
        [
            mo.md("Bus:"),
            busses_first,
            busses_previous,
            busses_select,
            busses_next,
            busses_last,
        ],
        justify="start",
    )
    return (bus_ui,)


@app.cell
def _(bus_ui, date_ui, mo):
    mo.hstack([date_ui,bus_ui])
    return


@app.cell
def _(mo, pd):
    with mo.status.spinner("Loading wecc240 load and DG data"):
        bus_load = (
            pd.read_csv("data/wecc240_bus_PD.csv.gz", index_col=[0], parse_dates=[0]) / 1000
        )
        bus_dg = (
            pd.read_csv("data/wecc240_dg.csv.gz", index_col=[0], parse_dates=[0]) / 1000
        )
        bus_net = bus_load - bus_dg
    return bus_dg, bus_load, bus_net


@app.cell
def _(bus_dg, bus_load, bus_net, busses_select, date_range, mo):
    _plt = bus_load.loc[date_range].sum(axis=1).plot()
    _plt.legend(["Total load", "Net load"])
    bus_net.loc[date_range].sum(axis=1).plot(
        ax=_plt,
        grid=True,
        xlabel="Date/Time (UTC)",
        ylabel="Load (GW)",
        figsize=(10, 7),
    )
    _f,_t = busses_select.value.split("-")
    mo.ui.tabs(
        {
            "Plot": mo.mpl.interactive(_plt),
            "Load (GW)": mo.ui.table(bus_load.loc[date_range,_f:_t].round(3), selection=None, page_size=24),
            "DG (GW)": mo.ui.table(bus_dg.loc[date_range,_f:_t].round(3), selection=None, page_size=24),
            "Net (GW)": mo.ui.table(
                bus_net.loc[date_range,_f:_t].round(3), selection=None, page_size=24
            ),
            "DG (%)": mo.ui.table(
                (bus_dg / bus_load * 100).loc[date_range,_f:_t].round(1), selection=None, page_size=24
            ),
        }
    )
    return


@app.cell
def _():
    import marimo as mo
    import datetime as dt
    import pandas as pd

    return dt, mo, pd


if __name__ == "__main__":
    app.run()
