import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook calibrates the bus loads based on the state energy consumption, as shown in Figure 1.
    """)
    return


@app.cell
def _(mo):
    mo.accordion({"Figure 1: Bus calibration data flow":mo.mermaid("""
    flowchart LR
        bus_mw.csv --> sum1
        bus_dg.csv -->|-| sum1
        sum1((+)) --> bus_net --> mul1
        bus_net --Σ
            hour--> bus_mwh

        state_mwh.csv -----> mul1
        subgraph State energy scaling
            bus_mwh --1/Σ
                state--> mul1
            mul1((x)) --> bus_load
        end

        weak_peak --> sum2
        subgraph WECC peak matching
            bus_load -- - non-caiso max -->sum2
            bus_load -- non-caiso --> sum2
        end
        sum2((+)) --> wecc_load

        subgraph CAISO peak matching
            bus_load -- - caiso max -->sum3
            bus_load -- caiso --> sum3
        end
        sum3((+)) --> wecc_load
        caiso_peak --> sum3
    """)})
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The WECC gis data (`wecc_gis`) is use to identify which busses are located in CAISO, i.e., `wecc_gis["BA"]="CA"`.
    """)
    return


@app.cell
def _(Counties, mo, pd):
    with mo.status.spinner("Reading WECC GIS data"):
        _counties = Counties(use_index="SYSTEM",selection="WECC")[["FIPS","COUNTY","ST"]].rename({"ST":"STATE"},axis=1)
        _counties["COUNTY"] = [f"{x} {y}" for x,y in _counties[["COUNTY","STATE"]].values]
        _wecc240 = pd.read_csv("../gis/wecc240.csv",converters={"BUS_I":str,"COUNTY":str}).rename({"COUNTY":"FIPS","GEOHASH":"NODE"},axis=1)
        wecc_gis = pd.merge(
            _wecc240,
            _counties,
            left_on="FIPS",
            right_on="FIPS",
        ).set_index("BUS_I")[["COUNTY","STATE","NODE","NAME","BA"]]
        wecc_busses = _wecc240[_wecc240["LOAD"]>0]["BUS_I"].tolist()
        caiso_busses = _wecc240[(_wecc240["LOAD"]>0)&(_wecc240["BA"]=="CA")]["BUS_I"].tolist()
        noncaiso_busses = list(set(wecc_busses) - set(caiso_busses))

    mo.accordion({"`wecc_gis`":wecc_gis})
    return caiso_busses, noncaiso_busses, wecc_busses, wecc_gis


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The date range is used to specify what range of data should be shown in table and plots. You can also specify whether only the date range is saved to the output file.
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
    constrain_ui = mo.ui.checkbox(label="Save only this date range")
    return constrain_ui, date_ui


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
def _(bus_ui, constrain_ui, date_ui, mo):
    mo.hstack([date_ui,constrain_ui,bus_ui],justify='start')
    return


@app.cell
def _(date_ui, pd):
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")[:-1]
    return (date_range,)


@app.cell
def _(busses_select, np):
    _busses = busses_select.value.split("-")
    bus_range = np.s_[_busses[0]:_busses[1]]
    return (bus_range,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The bus load (`bus_mw`) and bus distribution generation (`bus_dg`) are loaded from the files `bus_mw.csv.gz` and `bus_dg.csv.gz`, respectively.
    """)
    return


@app.cell
def _(bus_dg, mo, pd):
    with mo.status.spinner("Reading `bus_mw.csv.gz`"):
        bus_mw = pd.read_csv("bus_mw.csv.gz", index_col=[0], parse_dates=[0])[bus_dg.columns]
    return (bus_mw,)


@app.cell
def _(bus_mw, bus_range, date_range, mo):
    mo.accordion(
        {
            "`bus_mw`": mo.ui.table(
                bus_mw.loc[date_range,bus_range], selection=None, page_size=24
            ),
        }
    )
    return


@app.cell
def _(date_range, mo, pd):
    with mo.status.spinner("Reading `bus_dg.csv.gz`"):
        bus_dg = pd.read_csv("bus_dg.csv.gz", index_col=[0], parse_dates=[0])

    mo.accordion(
        {
            "`bus_dg`": mo.ui.table(
                bus_dg.loc[date_range], selection=None, page_size=24
            ),
        }
    )
    return (bus_dg,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The monthly state energy consumption (`state_mwh`) as reported by EIA in Form 861m is loaded from `state_mwh.csv`.
    """)
    return


@app.cell
def _(mo, net_mwh, pd):
    with mo.status.spinner("Reading `state_mwh.csv`"):
        state_mwh = pd.merge(
            pd.read_csv("state_mwh.csv", index_col=[1,0], parse_dates=[0])[["load"]].rename({"load":"eia"},axis=1),
            net_mwh,
            left_index=True,
            right_index=True,
        )
        state_mwh["calibration"] = state_mwh["eia"] / state_mwh["mwh"] 
    return (state_mwh,)


@app.cell
def _(bus_mw, date_range, mo, state_mwh):
    mo.accordion(
        {
            "`state_mwh`": mo.ui.table(
                state_mwh.round(4).reset_index()
                .set_index(["timestamp", "state"])
                .loc[bus_mw.loc[date_range].resample("MS").min().index],
                selection=None,
                page_size=len(state_mwh.index.get_level_values(1).unique()),
            ),
        }
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The bus-level net load (`bus_net`) and net monthly energy consumption (`bus_mwh`) are calculated from the bus load (`bus_mw`) and bus DG (`bus_dg`).
    """)
    return


@app.cell
def _(bus_dg, bus_mw, mo, pd, wecc_gis):
    with mo.status.spinner("Calibrating bus loads"):
        bus_net = (bus_mw - bus_dg).fillna(0)
        bus_mwh = bus_net.resample("MS").sum()
        net_mwh = pd.merge(
            bus_net.resample("MS").sum().T.rename_axis("bus"),
            wecc_gis[["STATE"]],
            left_index=True,
            right_index=True,
        ).groupby("STATE").sum().T.rename_axis("timestamp").stack().reset_index().rename({"STATE":"state",0:"mwh"},axis=1).set_index(["state","timestamp"])
    return bus_mwh, bus_net, net_mwh


@app.cell
def _(bus_mw, bus_mwh, bus_net, bus_range, date_range, mo):
    mo.accordion({
        "`bus_net`": bus_net.loc[date_range,bus_range],
        "`bus_mwh`": bus_mwh.loc[bus_mw.loc[date_range,bus_range].resample("MS").min().index],
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The calibrated bus load (`bus_load`) is calculated from the bus energy consumption (`bus_mwh`) and the reported state energy consumption (`state_mwh`) using the calibration factors (`calibration`).
    """)
    return


@app.cell
def _(bus_dg, bus_net, mo, pd, state_mwh, wecc_gis):
    with mo.status.spinner("Calibrating bus load to state energy consumption"):
        bus_load = bus_net.copy()
        _calibration = state_mwh.reset_index().set_index(["state","timestamp"])
        _all = []
        for _state in sorted(wecc_gis["STATE"].unique()):
            _scale = _calibration.loc[_state,"calibration"].resample("1h").ffill()
            for _bus in [x for x in wecc_gis[wecc_gis["STATE"]==_state].index if x in bus_load.columns]:
                bus_load[_bus] *= _scale
            _all.append(_scale.to_frame(_state))
        bus_load += bus_dg

    mo.accordion({"calibration":mo.ui.table(pd.concat(_all,axis=1).resample("MS").max().round(4),selection=None)})
    return (bus_load,)


@app.cell
def _(bus_load, bus_range, date_range, mo, wecc_busses):
    _df = bus_load.loc[date_range,wecc_busses]
    mo.accordion({
        "`bus_load`": mo.ui.tabs({
            "Data": _df.loc[:,bus_range].round(1),
            "Plot": _df.sum(axis=1).plot(grid=True)
        })
    })
    return


@app.cell
def _(bus_load, caiso_busses, date_range, wecc_busses):
    _loads = bus_load.loc[date_range,wecc_busses]
    wecc_high = _loads.sum(axis=1).max()/1e3
    caiso_high = _loads[caiso_busses].sum(axis=1).max()/1e3
    return


@app.cell
def _(mo):
    get_wecc_high,set_wecc_high = mo.state(None)
    def do_wecc_reset(*args,**kwargs):
        set_wecc_high(f"162.017")
    do_wecc_reset()
    wecc_reset_ui = mo.ui.button(label="Reset",on_click=do_wecc_reset)
    return get_wecc_high, set_wecc_high, wecc_reset_ui


@app.cell
def _(get_wecc_high, mo, set_wecc_high):
    wecc_high_ui = mo.ui.text(
        label=f"WECC peak adjustment (GW)",
        value=get_wecc_high(),
        on_change=set_wecc_high,
        debounce=True,
    )
    return (wecc_high_ui,)


@app.cell
def _(mo):
    get_caiso_high,set_caiso_high = mo.state(None)
    def do_caiso_reset(*args,**kwargs):
        set_caiso_high(f"47.121")
    do_caiso_reset()
    caiso_reset_ui = mo.ui.button(label="Reset",on_click=do_caiso_reset)
    return caiso_reset_ui, get_caiso_high, set_caiso_high


@app.cell
def _(get_caiso_high, mo, set_caiso_high):
    caiso_high_ui = mo.ui.text(
        label=f"CAISO peak adjustment (GW)",
        value=get_caiso_high(),
        on_change=set_caiso_high,
        debounce=True,
    )
    return (caiso_high_ui,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The WECC and CAISO loads are adjusted to match the specified peaks.
    """)
    return


@app.cell
def _(
    caiso_high_ui,
    caiso_offset_mw,
    caiso_reset_ui,
    mo,
    wecc_high_ui,
    wecc_offset_mw,
    wecc_reset_ui,
):
    _wecc_offset = "**invalid**" if wecc_offset_mw is None else f"{wecc_offset_mw/1e3:.3f} GW"
    _caiso_offset = "**invalid**" if caiso_offset_mw is None else f"{caiso_offset_mw/1e3:.3f} GW"
    mo.vstack([
        mo.hstack([wecc_high_ui,wecc_reset_ui,mo.md(f"(current WECC load adjustment is {_wecc_offset})")],justify='start'),
        mo.hstack([caiso_high_ui,caiso_reset_ui,mo.md(f"(current CAISO load adjustment is {_caiso_offset})")],justify='start'),
    ])
    return


@app.cell
def _(
    bus_dg,
    bus_load,
    caiso_busses,
    date_range,
    get_caiso_high,
    get_wecc_high,
    mo,
    noncaiso_busses,
    wecc_busses,
):
    with mo.status.spinner(f"Adjusting peak to {get_wecc_high()} GW"):
        wecc_load = bus_load.loc[:, wecc_busses].rename_axis("timestamp")

        _caisoload = wecc_load.loc[date_range, caiso_busses].sum(axis=1)
        _caisopeak = _caisoload.max()
        _caisopeaktime = _caisoload[_caisoload == _caisopeak].index.to_pydatetime()[0]

        _weccload = wecc_load.loc[date_range, wecc_busses].sum(axis=1)
        _weccpeak = _weccload.max()
        _weccpeaktime = _weccload[_weccload == _weccpeak].index.to_pydatetime()[0]

        try:
            _caiso = float(get_caiso_high())
            caiso_offset_mw = (
                _caiso * 1e3
                - wecc_load.loc[date_range, caiso_busses].sum(axis=1).max()
            )
            _weights = wecc_load.loc[date_range, caiso_busses].sum(
                axis=0
            ) / wecc_load.loc[date_range, caiso_busses].sum(axis=None)
            wecc_load.loc[:, caiso_busses] += caiso_offset_mw * _weights

        except:
            _caiso = 0
            if get_caiso_high():
                caiso_offset_mw = None
            else:
                caiso_offset_mw = 0

        try:
            _wecc = float(get_wecc_high())
            wecc_offset_mw = (
                _wecc * 1e3
                - wecc_load.loc[date_range, wecc_busses].sum(axis=1).max()
            ) + (0 if caiso_offset_mw is None else caiso_offset_mw)
            _weights = wecc_load.loc[date_range, noncaiso_busses].sum(
                axis=0
            ) / wecc_load.loc[date_range, noncaiso_busses].sum(axis=None)
            wecc_load.loc[:, noncaiso_busses] += wecc_offset_mw * _weights

        except:
            raise
            if get_wecc_high():
                wecc_offset_mw = None
            else:
                wecc_offset_mw = 0

        wecc_load.loc[:,wecc_busses] += bus_dg.loc[:,wecc_busses]
        _wecc_total = wecc_load.sum(axis=1).max()
        _caiso_total = wecc_load[caiso_busses].sum(axis=1).max()
        wecc_net = wecc_load - bus_dg
        caiso_net = wecc_net[caiso_busses]
        _wecc_net = wecc_net.loc[date_range].sum(axis=1).max()
        _caiso_net = caiso_net.loc[date_range].sum(axis=1).max()

    mo.md(f"""
    | System | Original Peak (GW) | Date/Time | Total Peak (GW) | Net peak (GW) | 
    | --- | --- | --- | --- | --- |
    | WECC | {_weccpeak/1000:.3f} | {_caisopeaktime:%m/%d/%y %H:%M %Z} | {_wecc_total/1000:.3f} |{(_wecc_net)/1000:.3f} |
    | CAISO | {_caisopeak/1000:.3f} | {_weccpeaktime:%m/%d/%y %H:%M %Z} | {_caiso_total/1000:.3f} |{(_caiso_net)/1000:.3f} |
    """)
    return caiso_offset_mw, wecc_load, wecc_net, wecc_offset_mw


@app.cell
def _(bus_range, date_range, mo, wecc_load):
    _df = (wecc_load.loc[date_range]/1000)
    mo.accordion({
        "`wecc_load`": mo.ui.tabs({
            "Data": (_df.loc[:,bus_range]*1000).round(1),
            "Plot": mo.mpl.interactive(_df.sum(axis=1).plot(grid=True,xlabel="Date/Time (UTC)",ylabel="Load (GW)")),
        })
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The following is a summary of the results.
    """)
    return


@app.cell
def _(bus_dg, mo, pd, save_range, wecc_load, wecc_net):
    _net = wecc_net.iloc[save_range].sum(axis=1) / 1000
    _load = wecc_load.iloc[save_range].sum(axis=1) / 1000
    _dg = bus_dg.iloc[save_range].sum(axis=1) / 1000
    _plt = _net.plot()
    _load.plot(linestyle=":",
        grid=True, figsize=(10, 7), xlabel="Date/Time (UTC)", ylabel="Load (GW)"
    )
    _plt.legend(["Net", "Load"])
    mo.ui.tabs(
        {
            "Data": mo.ui.table(
                pd.DataFrame(
                    {
                        "load": _load.round(3),
                        "dg": _dg.round(3),
                        "net": _net.round(3),
                    }
                ),
                selection=None,
                page_size=24,
            ),
            "Plot": mo.mpl.interactive(_plt),
        }
    )
    return


@app.cell
def _(constrain_ui, date_range, mo, np, wecc_load):
    _file = "wecc240_load.csv.gz"
    wecc_load
    _range = [wecc_load.index.tolist().index(x) for x in [date_range.min(),date_range.max()]] if constrain_ui.value else [8,-752]
    save_range = np.s_[_range[0]:_range[1]]
    def save(*args,**kwargs):
        with mo.status.spinner(f"Saving `{_file}`"):
            wecc_load.iloc[save_range].round(3).to_csv(_file,index=True,header=True,compression="gzip" if _file.endswith(".gz") else None)

    save_ui = mo.ui.button(label=f"Save `wecc_load` to `{_file}`",on_click=save)
    save_ui
    return (save_range,)


@app.cell
def _():
    import marimo as mo
    import datetime as dt
    import pandas as pd
    import numpy as np
    from fips import Counties

    return Counties, dt, mo, np, pd


if __name__ == "__main__":
    app.run()
