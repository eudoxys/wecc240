import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook gathers the state-level monthly energy production and consumption as reported to EIA.
    """)
    return


@app.cell
def _(Counties):
    states = Counties(use_index="SYSTEM",selection="WECC")["ST"].unique().tolist()
    return (states,)


@app.cell
def _(Form923, mo, pd, states):
    with mo.status.spinner("Reading Form923 (generation)"):
        gen = []
        for year in range(2018,2023):
            gen.append(Form923(year,states=states))
        gen = pd.concat(gen).groupby(["timestamp","state"]).sum().rename({"gen_mwh":"gen"},axis=1).round(3)

    mo.accordion({"`gen` (Form 923 data)":gen})
    return (gen,)


@app.cell
def _(HS861m, dt, mo, pd, states):
    with mo.status.spinner("Reading EIA HS861m (load)"):
        load = []
        for _year in range(2018, 2023):
            for _month in range(1, 13):
                _df = HS861m(_year, _month)[["tot_energy_mwh"]].reset_index()
                _df = _df[_df["state"].isin(states)]
                _df["timestamp"] = dt.datetime.strptime(
                    f"{_year}-{_month}-1 00:00:00+0000", "%Y-%m-%d %H:%M:%S%z"
                )
                load.append(_df)
        load = (
            pd.concat(load)
            .set_index(["timestamp", "state"])
            .rename({"tot_energy_mwh": "load"}, axis=1)
            .sort_index()
        )

    mo.accordion({"`load` (EIA HS861m data)": load})
    return (load,)


@app.cell
def _(Form861m, mo, pd, states):
    with mo.status.spinner("Reading Form 861m (DG)"):
        dg = []
        for _year in range(2018,2023):
            for _month in range(1,13):
                _df = Form861m(_year,_month)[["date","state","tot_mwh"]].rename({"date":"timestamp"},axis=1)
                dg.append(_df[_df["state"].isin(states)])
        dg = pd.concat(dg).set_index(["timestamp","state"]).rename({"tot_mwh":"dg"},axis=1).sort_index()

    mo.accordion({"`dg` (Form 861m data):": dg})
    return (dg,)


@app.cell
def _(dg, gen, load, pd):
    state_mwh = pd.concat([gen, load, dg], axis=1).fillna(0)
    state_mwh.to_csv("state_mwh.csv")
    return (state_mwh,)


@app.cell
def _(mo, states):
    state_ui = mo.ui.dropdown(options=states,label="State:")
    return (state_ui,)


@app.cell
def _(mo, state_mwh, state_ui):
    if state_ui.value is None:
        _df = state_mwh.groupby("timestamp").sum()/1e6
    else:
        _df = state_mwh.groupby(["state","timestamp"]).sum().loc[state_ui.value]/1e6
    _df.columns = [x for x in _df.columns]

    _plt = _df.plot(
        figsize=(10, 7),
        grid=True,
        ylabel="Monthly energy (TWH)",
        xlabel="Date/Time (UTC)",
        title="EIA Monthly Energy",
    )
    mo.accordion(
        {"`state_mwh` (consolidated EIA Form 923, Form 861m, and HS 861m)": 
             mo.ui.tabs({
                 "Data": mo.vstack([state_ui,mo.ui.table(_df.round(3),selection=None,page_size=12)]),
                 "Plot": mo.vstack([state_ui,mo.mpl.interactive(_plt)]),
             }),
        }
    )
    return


@app.cell
def _():
    import marimo as mo
    import datetime as dt
    import pandas as pd
    from eia import Form923, Form861m, HS861m
    from fips import Counties

    return Counties, Form861m, Form923, HS861m, dt, mo, pd


if __name__ == "__main__":
    app.run()
