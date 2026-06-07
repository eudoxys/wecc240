import marimo

__generated_with = "0.23.8"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook disaggregates county loads to WECC 240 busses as shown in Figure 1.
    """)
    return


@app.cell
def _(mo):
    mo.accordion({
        "Figure 1: County load disaggregation flowchart": mo.mermaid("""
    flowchart LR
        subgraph Load Data
            load[(county_mw.csv.gz)] --->|read_csv| county_mw
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
            county_mw -->|LOAD| node1 --> bus_mw
        end
        bus_mw -->|to_csv| output[(wecc240_load.csv.gz)]
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
    ## County loads data

    The county loads data (`county_mw`) is read from the file `county_mw.csv.gz`.
    """)
    return


@app.cell
def _(mo, pd):
    with mo.status.spinner("Reading county load data"):

        _nonus_mw = []

        # read loads (include non-US load busses)
        county_mw = pd.read_csv("county_mw.csv.gz",index_col=[0],parse_dates=[0])
        for _county,_bus in {
            "Alberta CANADA": "Canada/c2u6xt",
            "British Columbia CANADA": "Canada/c2c10y",
            "Mexicali MEXICO": "Mexico/9mtzm4",
            }.items():
            _nonus_mw.append(pd.read_csv(f"../{_bus}.csv",index_col=[0],parse_dates=[0])["load_MW"].to_frame(_county))
        county_mw = pd.concat(_nonus_mw+[county_mw],axis=1,sort=True)
    return (county_mw,)


@app.cell
def _(county_mw, mo):
    _pagewidth = 5
    get_counties_page, set_counties_page = mo.state(0)
    counties_pages = [
        f"{county_mw.columns[x]}-{county_mw.columns[min(x+_pagewidth,len(county_mw.columns))-1]}"
        for x in range(0, len(county_mw.columns), _pagewidth)
    ]
    counties_first = mo.ui.button(
        label="&lt;&lt;",
        on_click=lambda x: set_counties_page(0),
    )
    counties_previous = mo.ui.button(
        label="&lt;",
        on_click=lambda x: set_counties_page(max(0,get_counties_page() - 1)),
    )
    counties_next = mo.ui.button(
        label="&gt;",
        on_click=lambda x: set_counties_page(min(get_counties_page() + 1,len(counties_pages)-1)),
    )
    counties_last = mo.ui.button(
        label="&gt;&gt;",
        on_click=lambda x: set_counties_page(len(counties_pages)-1),
    )
    return (
        counties_first,
        counties_last,
        counties_next,
        counties_pages,
        counties_previous,
        get_counties_page,
        set_counties_page,
    )


@app.cell
def _(counties_pages, get_counties_page, mo, set_counties_page):
    counties_select = mo.ui.dropdown(
        options=counties_pages,
        value=counties_pages[get_counties_page()],
        on_change=lambda x: set_counties_page(counties_pages.index(x)),
    )
    return (counties_select,)


@app.cell
def _(
    counties_first,
    counties_last,
    counties_next,
    counties_previous,
    counties_select,
    date_ui,
    mo,
):
    counties_ui = mo.hstack(
        [
            date_ui,
            mo.hstack(
                [
                    mo.md("Counties:"),
                    counties_first,
                    counties_previous,
                    counties_select,
                    counties_next,
                    counties_last,
                ],
                justify="start",
            ),
        ]
    )
    return (counties_ui,)


@app.cell
def _(counties_select, counties_ui, county_mw, date_range, mo):
    mo.accordion({
        "`county_mw` (county total load data)": mo.vstack([
            counties_ui,
            county_mw.loc[date_range,counties_select.value.split("-")[0]:counties_select.value.split("-")[1]].round(3)])
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## WECC Model

    The list of all WECC counties is obtained from the `fips` module. The WECC GIS data (`wecc_gis`) is read from the `../gis/wecc240.csv` file and merged with the FIPS county data. Pseudo-counties for Alberta, British Columbia, and Mexicali are added to ensure that all busses in WECC are accounted for. The load busses (`load_bus`) are identified and the county contribution factors are computed.
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
        counties.drop(
            ["TZOFFSET", "DST", "RO", "COUNTY"],
            axis=1,
            inplace=True,
        )

        wecc_gis = pd.merge(
                pd.read_csv(
                    "../gis/wecc240.csv", converters={"COUNTY": str, "BUS_I": str}
                ).rename({"GEOHASH": "NODE"}, axis=1),
                counties[["FIPS", "COUNTY_ST"]],
                left_on="COUNTY",
                right_on="FIPS",
                how="left",
            ).drop(["COUNTY", "FIPS","GEN"], axis=1).set_index("BA")
        wecc_gis.loc["MX", "COUNTY_ST"] = "Mexicali MEXICO"
        wecc_gis.loc["AB", "COUNTY_ST"] = "Alberta CANADA"
        wecc_gis.loc["BC", "COUNTY_ST"] = "British Columbia CANADA"
        wecc_gis["ST"] = [x.split(" ")[-1] for x in wecc_gis["COUNTY_ST"]]
        wecc_gis = wecc_gis.reset_index().set_index("BUS_I").sort_index().reset_index()

        load_bus = wecc_gis[wecc_gis["LOAD"]>0].rename({"LOAD":"BUS_LOAD"},axis=1)
        load_bus = pd.merge(
            load_bus,
            load_bus.groupby(["COUNTY_ST"])["BUS_LOAD"]
            .sum()
            .to_frame("COUNTY_LOAD")
            .round(5),
            left_on="COUNTY_ST",
            right_on="COUNTY_ST",
        )
        load_bus["COUNTY_CF"] = (
            load_bus["BUS_LOAD"] / load_bus["COUNTY_LOAD"]
        ).round(6)

    mo.accordion(
        {
            "`counties` (WECC counties data)": counties[["COUNTY_ST","REGION","FIPS","LAT","LON","GEOHASH","ST"]],
            "`wecc_gis` (WECC model GIS data)": wecc_gis,
            "`load_bus` (WECC model load busses)": load_bus,
        },
        multiple=True,
    )
    return counties, load_bus, wecc_gis


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## County Aggregation

    Not all counties in WECC have nodes in the WECC model. This procedure determines which counties are aggregated on their proximmity to counties with nodes.
    """)
    return


@app.cell
def _(counties, county_mw, date_range, load_bus, mo, nearest, pd):
    with mo.status.spinner("Mapping county aggregations"):
        _nonus = ["Alberta CANADA", "British Columbia CANADA", "Mexicali MEXICO"]
        _mwh = (
            county_mw.loc[date_range]
            .sum(axis=0)
            .to_frame("MWH")
            .rename_axis("COUNTY_ST")
        )

        _mwh.round(1)
        county_map = pd.concat(
            [
                pd.DataFrame(
                    data={"COUNTY_AGGR": _nonus}, index=_nonus
                ).rename_axis("COUNTY_ST"),
                pd.DataFrame(
                    data={
                        "COUNTY_AGGR": [
                            nearest(x, load_bus)["COUNTY_ST"]
                            for _, x in counties.iterrows()
                        ],
                    },
                    index=counties["COUNTY_ST"],
                ),
            ]
        )
        county_map["ST"] = [x.split()[-1] for x in county_map.index]
        county_map["ST_AGGR"] = [x.split()[-1] for x in county_map["COUNTY_AGGR"]]
        county_map = pd.merge(county_map, _mwh, left_index=True, right_index=True)
        county_map = pd.merge(
            county_map,
            county_map.groupby("COUNTY_AGGR").sum()["MWH"].to_frame("COUNTY_MWH"),
            left_on="COUNTY_AGGR",
            right_index=True,
        )
        county_map["COUNTY_CF"] = county_map["MWH"] / county_map["COUNTY_MWH"]
        assert (
            county_map.groupby("COUNTY_AGGR")["COUNTY_CF"].sum().round(6) == 1
        ).all(), "county_map checksum failed"


    mo.accordion(
        {
            "`county_map` (mapping of counties without nodes to counties with nodes)": county_map.reset_index()
            .set_index(["ST", "COUNTY_ST"])
            .sort_index()
            .round(6)
        }
    )
    return (county_map,)


@app.cell
def _(county_map, county_mw, mo, pd):
    with mo.status.spinner("Aggregating county loads"):
        county_load = pd.DataFrame(
            data={
                x: [0] * len(county_mw.index)
                for x in county_mw.columns
            },
            index=county_mw.index,
        )
        for _county, _data in county_map.iterrows():
            county_load[_data["COUNTY_AGGR"]] += county_mw[_county]

    return (county_load,)


@app.cell
def _(counties_select, counties_ui, county_load, date_range, mo):
    mo.accordion(
        {
            "`county_load` (aggregation of counties loads)": mo.vstack(
                [
                    counties_ui,
                    county_load.loc[
                        date_range,
                        counties_select.value.split("-")[0] : counties_select.value.split("-")[1],
                    ].round(3),
                ]
            ),
        }
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Load Disaggregation

    The county loads (`county_load`) is disaggregated based on the load bus contribution factors to the nodes.
    """)
    return


@app.cell
def _(county_mw, load_bus, mo, pd, wecc_gis):
    with mo.status.spinner("Disaggregating county loads to busses"):
        bus_mw = pd.DataFrame(
            data={x:[0]*len(county_mw.index) for x in wecc_gis["BUS_I"]},
            index=county_mw.index,
        )
        for _bus,_county,_cf in load_bus[["BUS_I","COUNTY_ST","COUNTY_CF"]].values:
            bus_mw[_bus] += county_mw[_county] * _cf
    return (bus_mw,)


@app.cell
def _(bus_mw, mo):
    _pagewidth = 7
    get_busses_page, set_busses_page = mo.state(0)
    busses_pages = [
        f"{bus_mw.columns[x]}-{bus_mw.columns[min(x+_pagewidth,len(bus_mw.columns))-1]}"
        for x in range(0, len(bus_mw.columns), _pagewidth)
    ]
    busses_first = mo.ui.button(
        label="|&lt;",
        on_click=lambda x: set_busses_page(0),
    )
    busses_previous = mo.ui.button(
        label="&lt;",
        on_click=lambda x: set_busses_page(max(0,get_busses_page() - 1)),
    )
    busses_next = mo.ui.button(
        label="&gt;",
        on_click=lambda x: set_busses_page(min(get_busses_page() + 1,len(busses_pages)-1)),
    )
    busses_last = mo.ui.button(
        label="&gt;|",
        on_click=lambda x: set_busses_page(len(busses_pages)-1),
    )
    return (
        busses_first,
        busses_last,
        busses_next,
        busses_pages,
        busses_previous,
        get_busses_page,
        set_busses_page,
    )


@app.cell
def _(busses_pages, get_busses_page, mo, set_busses_page):
    busses_select = mo.ui.dropdown(
        options=busses_pages,
        value=busses_pages[get_busses_page()],
        on_change=lambda x: set_busses_page(busses_pages.index(x)),
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
    busses_ui = mo.hstack([
        mo.md("Bus:"),
        busses_first,
        busses_previous,
        busses_select,
        busses_next,
        busses_last,
    ],justify='start')
    return (busses_ui,)


@app.cell
def _(bus_mw, busses_select, busses_ui, date_range, date_ui, mo):
    mo.accordion({   
        "`bus_mw` (dataframe)": mo.vstack(
                [
                    mo.hstack([date_ui, busses_ui], justify="start"),
                    bus_mw.loc[date_range,busses_select.value.split("-")[0]:busses_select.value.split("-")[1]].round(3),
                ]
            ),
        }
    )
    return


@app.cell
def _(save_ui):
    save_ui
    return


@app.cell
def _(bus_mw, mo):
    def save(*args,**kwargs):
        with mo.status.spinner("Saving `bus_mw` to `bus_mw.csv.gz`"):
            bus_mw.round(3).to_csv("bus_mw.csv.gz",index=True,header=True,compression="gzip")

    save_ui = mo.ui.button(label="Save `bus_mw` to `bus_mw.csv.gz`",on_click=save)
    return (save_ui,)


@app.cell
def _():
    return


@app.cell
def _(bus_mw, county_load, county_mw, date_range):
    _ax = bus_mw.loc[date_range].sum(axis=1).to_frame("bus_mw").plot()
    county_load.loc[date_range].sum(axis=1).to_frame("county_load").plot(
        ax=_ax, marker="."
    )
    county_mw.loc[date_range].sum(axis=1).to_frame("county_mw").plot(
        ax=_ax, grid=True, xlabel="Date/Time (UTC)", ylabel="Load (MW)", color="k"
    )
    _ax.legend()
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import datetime as dt
    from fips import Counties
    from geohash import nearest2

    pd.options.display.width = None
    pd.options.display.max_columns = None


    def nearest(location, locations):
        """Find nearest node to a bus"""
        ix, ll, dist = nearest2(
            (location.LAT, location.LON), locations[["LAT", "LON"]].values
        )
        return locations.iloc[ix]

    return Counties, dt, mo, nearest, pd


if __name__ == "__main__":
    app.run()
