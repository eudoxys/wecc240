import marimo

__generated_with = "0.23.14"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook disaggregates node DG to WECC 240 busses as shown in Figure 1.
    """)
    return


@app.cell
def _(mo):
    mo.accordion({
        "Figure 1: Nodal DG disaggregation flowchart": mo.mermaid("""
    flowchart LR

        nlr@{ shape: docs, label: "NLR"} --> dg
        eudoxys@{ shape: docs, label="Eudoxys"} --> fips

        subgraph DG Data
            dg[(node_dg.csv.gz)] --->|read_csv| node_dg
        end
        subgraph WECC Model
            fips[(fips.Counties)] -->|system=WECC| wecc_gis
            gis[(../gis/wecc240.csv)] -->|read_csv| wecc_gis
        end
        subgraph Bus Contributions
            wecc_gis -->|LOAD>0| load_bus 
        end
        subgraph DG Disaggregation
            load_bus -->|CF| node1((x))
            node_dg -->|DG| node1 --> bus_dg
        end
        bus_dg -->|to_csv| output[(wecc240_dg.csv.gz)]
    """)})
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## DG data

    The distributed generation data (`node_dg`) is read from the file `node_dg.csv.gz` and resampled the mean hourly power.
    """)
    return


@app.cell
def _(mo, pd):
    with mo.status.spinner("Reading node DG data"):
        # read node DG (include non-US zero values)
        node_dg = (
            (pd.read_csv("node_dg.csv.gz", index_col=[0], parse_dates=[0]) / 1000)
            .round(3)
            .resample("1h")
            .mean()
        )
        node_dg.columns = [x.split("_")[0] for x in node_dg.columns]
        _nonus_dg = []
        for _county, _bus in {
            "Alberta CANADA": "Canada/c2u6xt",
            "British Columbia CANADA": "Canada/c2c10y",
            "Mexicali MEXICO": "Mexico/9mtzm4",
        }.items():
            _nonus_dg.append(
                pd.DataFrame(
                    {_bus.split("/")[1]: [0] * len(node_dg.index)},
                    index=node_dg.index,
                )
            )
        node_dg = pd.concat(_nonus_dg + [node_dg], axis=1, sort=True)
        node_dg = node_dg[sorted(node_dg.columns)]
        node_dg.rename_axis("timestamp")
    return (node_dg,)


@app.cell
def _(mo, node_dg):
    _pagewidth = 7
    get_nodes_page, set_nodes_page = mo.state(0)
    nodes_pages = [
        f"{node_dg.columns[x]}-{node_dg.columns[min(x+_pagewidth,len(node_dg.columns))-1]}"
        for x in range(0, len(node_dg.columns), _pagewidth)
    ]
    nodes_first = mo.ui.button(
        label="|&lt;",
        on_click=lambda x: set_nodes_page(0),
    )
    nodes_previous = mo.ui.button(
        label="&lt;",
        on_click=lambda x: set_nodes_page(max(0,get_nodes_page() - 1)),
    )
    nodes_next = mo.ui.button(
        label="&gt;",
        on_click=lambda x: set_nodes_page(min(get_nodes_page() + 1,len(nodes_pages)-1)),
    )
    nodes_last = mo.ui.button(
        label="&gt;|",
        on_click=lambda x: set_nodes_page(len(nodes_pages)-1),
    )
    return (
        get_nodes_page,
        nodes_first,
        nodes_last,
        nodes_next,
        nodes_pages,
        nodes_previous,
        set_nodes_page,
    )


@app.cell
def _(get_nodes_page, mo, nodes_pages, set_nodes_page):
    nodes_select = mo.ui.dropdown(
        options=nodes_pages,
        value=nodes_pages[get_nodes_page()],
        on_change=lambda x: set_nodes_page(nodes_pages.index(x)),
    )
    return (nodes_select,)


@app.cell
def _(
    date_ui,
    mo,
    nodes_first,
    nodes_last,
    nodes_next,
    nodes_previous,
    nodes_select,
):
    nodes_ui = mo.hstack(
        [
            date_ui,
            mo.md("Nodes:"),
            nodes_first,
            nodes_previous,
            nodes_select,
            nodes_next,
            nodes_last,
        ],
    justify="start",
    )
    return (nodes_ui,)


@app.cell
def _(date_range, mo, node_dg, nodes_select, nodes_ui):
    _df = node_dg.loc[
        date_range,
        nodes_select.value.split("-")[0] : nodes_select.value.split("-")[1],
    ].round(3)
    _plt = _df.plot(
        figsize=(10, 7),
        title="Node DG",
        xlabel="Date/Time (UTC)",
        ylabel="DG (MW)",
        grid=True,
    )
    mo.accordion(
        {
            "`node_dg` (hourly DG data at the node level)": mo.vstack(
                [
                    nodes_ui,
                    mo.ui.tabs(
                        {
                            "Data": mo.ui.table(_df,selection=None,page_size=24),
                            "Plot": mo.mpl.interactive(_plt),
                        }
                    ),
                ]
            ),
        }
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## WECC Model

    The WECC model data is read from the `../gis/wecc240.csv` file and merged with the FIPS county data. Pseudo-counties for Alberta, British Columbia, and Mexicali are added to ensure that all busses in WECC are accounted for.
    """)
    return


@app.cell
def _(Counties, mo, pd):
    with mo.status.spinner("Loading WECC model"):
        counties = (
            Counties(use_index=["SYSTEM"], selection=["WECC"])
            .sort_values(["ST", "COUNTY"])
            .reset_index(drop=True)
        )
        counties["COUNTY_ST"] = [
            f"{x} {y}" for x, y in counties[["COUNTY", "ST"]].values
        ]
        counties.drop(["LAT","LON","TZOFFSET","DST","RO","ST","COUNTY"],axis=1,inplace=True)

        wecc_gis = (
            pd.merge(
                pd.read_csv(
                    "../gis/wecc240.csv", converters={"COUNTY": str, "BUS_I": str}
                ).rename({"GEOHASH": "NODE"}, axis=1),
                counties[["FIPS", "COUNTY_ST"]],
                left_on="COUNTY",
                right_on="FIPS",
                how="outer",
            )
            .drop(["COUNTY", "FIPS", "LAT", "LON"], axis=1)
            .set_index("BA")
        )
        wecc_gis.loc["MX", "COUNTY_ST"] = "Mexicali MEXICO"
        wecc_gis.loc["AB", "COUNTY_ST"] = "Alberta CANADA"
        wecc_gis.loc["BC", "COUNTY_ST"] = "British Columbia CANADA"
        wecc_gis = (
            wecc_gis.reset_index().set_index("BUS_I").sort_index().reset_index()
        )

    mo.accordion(
        {
            "`counties` (WECC counties data)": counties[["COUNTY_ST","REGION","FIPS","GEOHASH"]],
            "`wecc_gis` (WECC model GIS data)": wecc_gis,
        },
        multiple=True,
    )
    return (wecc_gis,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Bus Contributions

    The load busses are identified based on the non-zero load values in the original WECC model. The bus contribution factors to nodes are computed and stored for later use in node DG disaggregation.
    """)
    return


@app.cell
def _(mo, pd, wecc_gis):
    with mo.status.spinner("Mapping nodes to busses"):
        load_bus = wecc_gis[wecc_gis["LOAD"] > 0][
            ["BUS_I", "NODE", "COUNTY_ST", "NAME", "LOAD"]
        ].rename({"LOAD": "BUS_LOAD"}, axis=1)
        load_bus = pd.merge(
            load_bus,
            load_bus.groupby(["NODE"])["BUS_LOAD"]
            .sum()
            .to_frame("NODE_LOAD")
            .round(5),
            left_on="NODE",
            right_on="NODE",
        )
        load_bus["NODE_BUS_CF"] = (
            load_bus["BUS_LOAD"] / load_bus["NODE_LOAD"]
        ).round(6)

    mo.accordion(
        {
            "`load_bus` (load bus contributions to nodes and counties)": load_bus,
        },
        multiple=True,
    )
    return (load_bus,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## DG Disaggregation

    The node DG is disaggregated based on the load bus contribution factors to the nodes.
    """)
    return


@app.cell
def _(load_bus, mo, node_dg, pd):
    with mo.status.spinner("Disaggregating node DG to busses"):
        bus_dg = pd.DataFrame(
            {x: [0] * len(node_dg.index) for x in load_bus["BUS_I"]},
            index=node_dg.index,
        ).rename_axis("timestamp")
        _loadnodes = load_bus.set_index("NODE")
        _done = []
        for _node in node_dg.columns:
            for _n, _data in _loadnodes.loc[[_node]].iterrows():
                _bus = _data["BUS_I"]
                _cf = _data["NODE_BUS_CF"]
                bus_dg[_bus] += node_dg[_node] * _cf
        # assert (
        #     bus_dg.loc[:, bus_dg.max(axis=0) == 0].columns
        #     == ["2000", "5001", "5002", "5003"]
        # ).all(), (
        #     f"incorrect DG mapping (only CANADA and MEXICO should have zero DG)"
        # )
    return (bus_dg,)


@app.cell
def _(load_bus, mo):
    _options = {
        f"{x} ({y})": x
        for x, y in load_bus.set_index("NODE")[["NAME"]].to_dict()["NAME"].items()
    }
    node_ui = mo.ui.dropdown(options=_options, label="Node")
    return (node_ui,)


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
def _(
    bus_dg,
    bus_ui,
    busses_select,
    date_range,
    date_ui,
    load_bus,
    mo,
    node_dg,
    node_ui,
):
    _loadnodes = load_bus.set_index("NODE")
    _df = bus_dg.loc[
        date_range,
        busses_select.value.split("-")[0] : busses_select.value.split("-")[1],
    ].round(3)
    if node_ui.value is None:
        _plt = (bus_dg.loc[date_range].sum(axis=1) / 1000).plot(kind="area")
        _plt = (node_dg.loc[date_range].sum(axis=1) / 1000).plot(
            ax=_plt,
            figsize=(10, 7),
            xlabel="Date/Time (UTC)",
            ylabel="DG (GW)",
            title="WECC DG",
            grid=True,
        )
    else:
        _bus = _loadnodes.loc[node_ui.value, "BUS_I"]
        _bus = [_bus] if isinstance(_bus, str) else _bus.tolist()
        _node = _loadnodes.loc[node_ui.value, "NAME"]
        _plt = bus_dg.loc[date_range, _bus].plot(kind="area")
        _plt = node_dg.loc[date_range, node_ui.value].plot(
            ax=_plt,
            figsize=(10, 7),
            xlabel="Date/Time (UTC)",
            ylabel="DG (MW)",
            title=f"{node_ui.selected_key} DG",
            grid=True,
        )
        _plt.legend()

    mo.accordion(
        {
            "bus_dg": mo.ui.tabs(
                {
                    "Data": mo.vstack(
                        [
                            mo.hstack([date_ui, bus_ui], justify="start"),
                            mo.ui.table(_df,selection=None,page_size=24),
                        ]
                    ),
                    "Plot": mo.vstack(
                        [
                            mo.hstack([date_ui, node_ui], justify="start"),
                            mo.mpl.interactive(_plt),
                        ]
                    ),
                }
            ),
        }
    )
    return


@app.cell
def _(bus_dg, mo):
    def save(*args,**kwargs):
        with mo.status.spinner("Saving `bus_dg` to `bus_dg.csv.gz`"):
            bus_dg.round(3).to_csv("bus_dg.csv.gz",index=True,header=True,compression="gzip")

    save_ui = mo.ui.button(label="Save `bus_dg` to `bus_dg.csv.gz`",on_click=save)
    save_ui
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import datetime as dt
    from fips import Counties

    pd.options.display.width = None
    pd.options.display.max_columns = None
    return Counties, dt, mo, pd


if __name__ == "__main__":
    app.run()
