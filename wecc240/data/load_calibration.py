import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook calibrates the WECC county loads to CAISO and WECC peaks in August 2020.
    """)
    return


@app.cell
def _(Counties, pd):
    def county_st(x):
        return [f"{x} {y}" for x, y in x[["COUNTY", "ST"]].values]

    nonus = {
        "Alberta CANADA":"../Canada/c2u6xt.csv",
        "British Columbia CANADA":"../Canada/c2c10y.csv",
        "Mexicali MEXICO":"../Mexico/9mtzm4.csv",
    }
    _counties = Counties(use_index=["SYSTEM"], selection=["WECC"]).sort_values(
        ["ST", "COUNTY"]
    )
    wecc_counties = county_st(_counties)
    wecc_states = sorted(_counties["ST"].unique())
    wecc_gis = pd.read_csv("../gis/wecc240.csv",converters={"COUNTY":str}).rename({"GEOHASH":"NODE"},axis=1)
    caiso_nodes = wecc_gis.set_index("BA").loc["CA"]["NODE"].unique().tolist()
    caiso_counties = county_st(_counties.set_index("REGION").loc["CAISO"])
    noncaiso_counties = list(set(wecc_counties) - set(caiso_counties)) + list(nonus)
    return caiso_counties, noncaiso_counties, nonus


@app.cell
def _(mo, nonus, pd):
    with mo.status.spinner("Reading county load and DG data"):
        _us = pd.read_csv("county_mw.csv.gz",index_col=[0],parse_dates=[0])
        _nonus = [pd.read_csv(y,index_col=[0],parse_dates=[0])["load_MW"].to_frame(x) for x,y in nonus.items()]
        county_mw = pd.concat(_nonus+[_us],axis=1,sort=True)
        _dg = pd.read_csv("county_dg.csv.gz",index_col=[0],parse_dates=[0])
        _nonus = [pd.DataFrame({x:[0]*len(_dg.index)},_dg.index) for x in nonus]
        county_dg = pd.concat(_nonus+[_dg],axis=1,sort=True)
    return county_dg, county_mw


@app.cell
def _(mo):
    reset_ui = mo.ui.button(label="Reset")
    return (reset_ui,)


@app.cell
def _(mo, reset_ui):
    reset_ui.value
    caiso_peak_ui = mo.ui.number(value=47.121,debounce=True)
    total_peak_ui = mo.ui.number(value=162.017,debounce=True)
    return caiso_peak_ui, total_peak_ui


@app.cell
def _(county_mw, dt, mo):
    date_ui = mo.ui.date_range(
        label="Date range:",
        start=min(county_mw.index).date(),
        stop=max(county_mw.index).date(),
        value=(dt.date(2020, 8, 14), dt.date(2020, 8, 21)),
    )
    return (date_ui,)


@app.cell
def _(date_ui, pd):
    date_range = pd.date_range(start=date_ui.value[0],end=date_ui.value[1],freq="1h",tz="UTC")
    return (date_range,)


@app.cell
def _(caiso_counties, county_mw, date_range, noncaiso_counties):
    wecc_peak_mw = county_mw.loc[date_range][noncaiso_counties].sum(axis=1).max()
    caiso_peak_mw = county_mw.loc[date_range][caiso_counties].sum(axis=1).max()
    return caiso_peak_mw, wecc_peak_mw


@app.cell
def _(caiso_counties, county_dg, date_range, noncaiso_counties):
    wecc_peak_dg = county_dg.loc[date_range][noncaiso_counties].sum(axis=1).max()
    caiso_peak_dg = county_dg.loc[date_range][caiso_counties].sum(axis=1).max()
    return caiso_peak_dg, wecc_peak_dg


@app.cell
def _(caiso_counties, county_dg, county_mw, date_range, noncaiso_counties):
    wecc_peak_net = (county_mw-county_dg).loc[date_range][noncaiso_counties].sum(axis=1).max()
    caiso_peak_net = (county_mw-county_dg).loc[date_range][caiso_counties].sum(axis=1).max()
    return caiso_peak_net, wecc_peak_net


@app.cell
def _(caiso_peak_net, caiso_peak_ui, total_peak_ui, wecc_peak_net):
    wecc_scale = (total_peak_ui.value-caiso_peak_ui.value) / (wecc_peak_net/1000)
    caiso_scale = caiso_peak_ui.value / (caiso_peak_net/1000)
    return caiso_scale, wecc_scale


@app.cell
def _(caiso_counties, caiso_scale, county_mw, noncaiso_counties, wecc_scale):
    county_load = county_mw.copy()
    county_load[noncaiso_counties] *= wecc_scale
    county_load[caiso_counties] *= caiso_scale
    wecc_peak_calibrated = county_load[noncaiso_counties].sum(axis=1).max()
    caiso_peak_calibrated = county_load[caiso_counties].sum(axis=1).max()
    return caiso_peak_calibrated, wecc_peak_calibrated


@app.cell
def _(date_ui):
    date_ui
    return


@app.cell
def _(
    caiso_peak_calibrated,
    caiso_peak_dg,
    caiso_peak_mw,
    caiso_peak_ui,
    caiso_scale,
    mo,
    reset_ui,
    total_peak_ui,
    wecc_peak_calibrated,
    wecc_peak_dg,
    wecc_peak_mw,
    wecc_scale,
):
    mo.md(f"""
    |  | CAISO Peak | non-CAISO Peak | WECC Peak | |
    | ---------- | ----- | ---- | --- | --- |
    | **Model total load** | {caiso_peak_mw/1000:.3f} GW | {wecc_peak_mw/1000:.3f} GW | {(wecc_peak_mw+caiso_peak_mw)/1000:.3f} GW |
    | **Model DG** | {caiso_peak_dg/1000:.3f} GW | {wecc_peak_dg/1000:.3f} GW | {(wecc_peak_dg+caiso_peak_dg)/1000:.3f} GW |
    | **Target net peak** | {caiso_peak_ui} GW | {total_peak_ui.value-caiso_peak_ui.value:.3f} GW | {total_peak_ui} GW | {reset_ui} |
    | **Peak calibration factor** | {caiso_scale:.3f} | {wecc_scale:.3f} |
    | **Calibrated total peak** | {caiso_peak_calibrated/1000:.3f} GW | {wecc_peak_calibrated/1000:.3f} GW | {(caiso_peak_calibrated+wecc_peak_calibrated)/1000:.3f} GW |
    | **Calibrated net peak** | {(caiso_peak_calibrated-caiso_peak_dg)/1000:.3f} GW | {(wecc_peak_calibrated-wecc_peak_dg)/1000:.3f} GW | {(caiso_peak_calibrated-caiso_peak_dg+wecc_peak_calibrated-wecc_peak_dg)/1000:.3f} GW
    """)
    return


@app.cell
def _(
    caiso_counties,
    caiso_scale,
    county_dg,
    county_mw,
    noncaiso_counties,
    wecc_scale,
):
    calibrated_mw = county_mw.copy()
    calibrated_mw[caiso_counties] *= caiso_scale
    calibrated_mw[noncaiso_counties] *= wecc_scale
    calibrated_net = calibrated_mw - county_dg
    return calibrated_mw, calibrated_net


@app.cell
def _(mo):
    caiso_ui = mo.ui.checkbox(label="Show CAISO only")
    caiso_ui
    return (caiso_ui,)


@app.cell
def _(
    caiso_counties,
    caiso_ui,
    calibrated_mw,
    calibrated_net,
    county_dg,
    date_range,
    mo,
    noncaiso_counties,
    plot,
):
    _counties = caiso_counties + ([] if caiso_ui.value else noncaiso_counties)
    mo.ui.tabs({
        "Plot": plot,
        "Data": mo.ui.tabs({
            "Load": calibrated_mw.loc[date_range][_counties].round(3),
            "DG": county_dg.loc[date_range][_counties].round(3),
            "Net": calibrated_net.loc[date_range][_counties].round(3),
        })
    })
    return


@app.cell
def _(
    caiso_counties,
    caiso_ui,
    calibrated_mw,
    calibrated_net,
    date_range,
    mo,
    noncaiso_counties,
):
    with mo.status.spinner("Generating plot"):
        _options = dict(
            grid=True,
            figsize=(10, 7),
            title=f"{'CAISO' if caiso_ui.value else 'WECC'} calibrated county loads",
            xlabel="Date/Time (UTC)",
            ylabel="Load (GW)",
        )
        _counties = caiso_counties + ([] if caiso_ui.value else noncaiso_counties)
        plot = (calibrated_mw.loc[date_range][_counties].sum(axis=1) / 1000).plot()
        (calibrated_net.loc[date_range][_counties].sum(axis=1) / 1000).plot(
            ax=plot, **_options
        )
        plot.legend(["Total load", "Net Load"])
    return (plot,)


@app.cell
def _(calibrated_mw, date_range, mo):
    def save(*args,**kwargs):
        with mo.status.spinner("Saving calibrated loads to `county_total.csv.gz`"):
            _range = calibrated_mw.index if all_ui.value else date_range
            calibrated_mw.loc[_range].round(3).to_csv("county_total.csv.gz",index=True,compression="gzip")
        mo.md("Calibrated load saved to `county_total.csv.gz`")

    save_ui = mo.ui.button(label="Save to `county_total_csv.gz`",on_click=save)
    all_ui = mo.ui.checkbox(label="Save all data")
    return all_ui, save_ui


@app.cell
def _(all_ui, mo, save_ui):
    mo.hstack([all_ui,save_ui],justify='start')
    return


@app.cell
def _():
    # county_dg.T[county_dg.sum(axis=0)>0].T.columns
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import datetime as dt
    from fips import Counties

    return Counties, dt, mo, pd


if __name__ == "__main__":
    app.run()
