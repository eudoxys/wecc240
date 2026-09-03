import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(r"""
    This notebook compares the CAISO EMS load data to the WECC240 model.
    """)
    return


@app.cell
def _(os, pd):
    data = []
    _dir = "../CAISO"
    for file in sorted([os.path.join(_dir,x) for x in os.listdir(_dir) if x.startswith("historicalemshourlyload-") and x.endswith(".xlsx")]):
        _data = pd.read_excel(file,index_col=[0, 1],parse_dates=[0],usecols=[0, 1, 6],).round(3)
        _data.columns = ["caiso_mw"]
        data.append(_data)
    data = pd.concat(data,axis=0).sort_index()
    # print(data)
    data.index = (
        data.index.get_level_values(0)
        + pd.to_timedelta(data.index.get_level_values(1) + 7, unit="h")
    ).tz_localize("UTC").tz_convert("US/Pacific")
    _data = pd.DataFrame(
        {"caiso_mw":float('nan')},
        index=pd.date_range(start=data.index[0],end=data.index[-1],freq="1h"),
    )
    _data.loc[data.index,"caiso_mw"] = data["caiso_mw"]
    data = _data.interpolate(method='time')
    return (data,)


@app.cell
def _(data, mo):
    mo.mpl.interactive((data/1000).plot(figsize=(10,7),grid=True,ylabel="Load (GW)"))
    return


@app.cell
def _(data):
    data.resample("YS").max().plot(grid=True)
    return


@app.cell
def _(data):
    ax = data.resample("MS").max()["caiso_mw"].to_frame("Maximum load").plot()
    (data.resample("MS").mean()+3*data.resample("MS").std())["caiso_mw"].to_frame("+3$\\sigma$ load").plot(ax=ax)
    data.resample("MS").mean()["caiso_mw"].to_frame("Mean load").plot(ax=ax)
    (data.resample("MS").mean()-3*data.resample("MS").std())["caiso_mw"].to_frame("-3$\\sigma$ load").plot(ax=ax)
    data.resample("MS").min()["caiso_mw"].to_frame("Minimum load").plot(ax=ax,figsize=(10,7),grid=True)
    return


@app.cell
def _():
    import marimo as mo
    import os
    import pandas as pd
    return mo, os, pd


if __name__ == "__main__":
    app.run()
