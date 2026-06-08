import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook calibrates the bus loads based on the state energy consumption, as shown in Figure 1.
    """)
    return


@app.cell
def _(mo):
    mo.mermaid("""
    flowchart LR
        bus_mw.csv --> sum1
        bus_dg.csv -->|-| sum1
        sum1((+)) --> bus_net --> mul1
        bus_net --Σ
            hour--> bus_mwh
        state_mwh.csv -----> mul1
        bus_mwh --1/Σ
            state--> mul1
        mul1((x)) --> bus_load.csv
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
def _(date_ui):
    date_ui
    return


@app.cell
def _(date_ui, pd):
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")[:-1]
    return (date_range,)


@app.cell
def _(date_range, mo, pd):
    with mo.status.spinner("Reading `bus_mw.csv.gz`"):
        bus_mw = pd.read_csv("bus_mw.csv.gz", index_col=[0], parse_dates=[0])

    mo.accordion(
        {
            "`bus_mw`": mo.ui.table(
                bus_mw.loc[date_range], selection=None, page_size=24
            ),
        }
    )
    return (bus_mw,)


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
def _(bus_mw, bus_mwh, bus_net, date_range, mo):
    mo.accordion({
        "`bus_net`": bus_net.loc[date_range],
        "`bus_mwh`": bus_mwh.loc[bus_mw.loc[date_range].resample("MS").min().index],
    })
    return


@app.cell
def _(bus_dg, bus_net, state_mwh, wecc_gis):
    bus_load = bus_net.copy()
    _calibration = state_mwh.reset_index().set_index(["state","timestamp"])
    for _state in sorted(wecc_gis["STATE"].unique()):
        _scale = _calibration.loc[_state,"calibration"].resample("1h").ffill()
        for _bus in wecc_gis[wecc_gis["STATE"]==_state].index:
            bus_load[_bus] *= _scale
    bus_load += bus_dg
    return (bus_load,)


@app.cell
def _(bus_load, date_range, mo, wecc_busses):
    _df = bus_load.loc[date_range,wecc_busses]
    mo.accordion({
        "`bus_load`": mo.ui.tabs({
            "Data": _df.round(1),
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

    mo.md(f"""
    | | Peak | Date/Time | Adjusted Peak |
    | --- | --- | --- | --- |
    | CAISO | {_caisopeak/1000:.3f} GW | {_weccpeaktime:%m/%d/%y %H:%M %Z} | {(_caisopeak+caiso_offset_mw)/1000:.3f} GW |
    | WECC | {_weccpeak/1000:.3f} GW | {_caisopeaktime:%m/%d/%y %H:%M %Z} | {(_weccpeak+wecc_offset_mw)/1000:.3f} 

    """)
    return caiso_offset_mw, wecc_load, wecc_offset_mw


@app.cell
def _(date_range, mo, wecc_load):
    _df = (wecc_load.loc[date_range]/1000)
    mo.accordion({
        "`wecc_load`": mo.ui.tabs({
            "Data": (_df*1000).round(1),
            "Plot": mo.mpl.interactive(_df.sum(axis=1).plot(grid=True,xlabel="Date/Time (UTC)",ylabel="Load (GW)")),
        })
    })
    return


@app.cell
def _(mo, wecc_load):
    _file = "wecc240_load.csv.gz"
    wecc_load
    def save(*args,**kwargs):
        with mo.status.spinner(f"Saving `{_file}`"):
            wecc_load.round(3).to_csv(_file,index=True,header=True,compression="gzip" if _file.endswith(".gz") else None)

    save_ui = mo.ui.button(label=f"Save `wecc_load` to `{_file}`",on_click=save)
    save_ui
    return


@app.cell
def _():
    import marimo as mo
    import datetime as dt
    import pandas as pd
    from fips import Counties

    return Counties, dt, mo, pd


if __name__ == "__main__":
    app.run()
