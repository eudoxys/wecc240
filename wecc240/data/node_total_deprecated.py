import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook aggregates county total loads to bus totals prior to including DG, as follows:
    """)
    return


@app.cell
def _(mo):
    mo.mermaid("""
    flowchart LR
        county_node.csv[(**county_node.csv**)] --->|county_node| aggregate
        county_total.csv.gz[(**county_total.csv.gz**)] --->|county_total| aggregate
        aggregate([groupby.node.sum]) --> mul1
        mul1((x)) --> node_total[(**node_total.csv.gz**)]

        state_pop.csv[(**state_pop.csv**)] --> resample
        state_pop.csv -->|1/loc:2018-01-01| mul2
        resample([resample.month]) --> mul2
        mul2((x)) -->|load_growth| mul1
    """)
    return


@app.cell
def _(mo, pd):
    with mo.status.spinner("Loading `county_node.csv`..."):
        county_node = pd.read_csv("county_node.csv",index_col=["county_st"],usecols=["county_st","node"])
    return (county_node,)


@app.cell
def _(mo, pd):
    with mo.status.spinner("Loading `county_total.csv.gz`..."):
        county_total = pd.read_csv("county_total.csv.gz",index_col=[0],parse_dates=[0])
    return (county_total,)


@app.cell
def _(Counties):
    states = Counties(use_index="SYSTEM",selection="WECC")["ST"].unique().tolist()
    return (states,)


@app.cell
def _(county_total, dt, pd):
    _years = county_total.index.year.unique().tolist()
    _start_end = dict(start=dt.datetime(min(_years),1,1,0,0,0),end=dt.datetime(max(_years)+1,1,1,0,0,0,))
    year_range = pd.date_range(**_start_end,freq="YS").tz_localize("UTC")[:-1]
    month_range = pd.date_range(**_start_end,freq="MS").tz_localize("UTC")[:-1]
    hour_range = pd.date_range(**_start_end,freq="1h").tz_localize("UTC")[:-1]
    return (hour_range,)


@app.cell
def _(hour_range, mo, pd, states):
    with mo.status.spinner("Loading `state_pop.csv`..."):
        _pop = pd.read_csv(
            "state_pop.csv", index_col=[0], parse_dates=[1]
        ).loc[states]
        _pop["Year"] = pd.DatetimeIndex(_pop["Year"]).tz_localize("UTC")
        _pop.set_index("Year", append=True, inplace=True)
        load_growth = []
        for _state in states:
            _hourly = _pop.loc[_state].resample("MS").interpolate().resample("1h").ffill().loc[hour_range]/1e6
            _hourly.columns = [_state]
            _ref = _hourly.iloc[0][_state]
            load_growth.append((_hourly/_ref).round(6))
    load_growth = pd.concat(load_growth,axis=1).rename_axis("timestamp").sort_index()
    return (load_growth,)


@app.cell
def _(county_node, county_total, load_growth, mo, pd):
    with mo.status.progress_bar(title="Aggregating counties...",total=len(county_total.columns),remove_on_exit=True) as _bar:
        node_total = pd.DataFrame(
            data={x:[0]*len(county_total.index) for x in county_node["node"].unique()},
            index=county_total.index,
        )
        for _county_st in county_total.columns:
            _state = _county_st.split()[-1]
            _bar.update(subtitle=_county_st)
            _node = county_node.loc[_county_st,"node"]
            node_total[_node] += county_total[_county_st] * load_growth[_state]
        node_total = node_total[sorted(node_total.columns)]
    return (node_total,)


@app.cell
def _(county_node, county_total, load_growth, mo, node_total):
    mo.accordion({
        "load_growth": mo.ui.table(load_growth,selection=None,page_size=24),
        "county_node": mo.ui.table(county_node,selection=None,page_size=16),
        "county_total": mo.ui.table(county_total.round(3),selection=None,page_size=24),
        "node_total": mo.ui.table(node_total.round(3),selection=None,page_size=24),
    }, multiple=True)
    return


@app.cell
def _(county_total, mo):
    mo.mpl.interactive(county_total["Amador CA"].plot(figsize=(10,6),grid=True))
    return


@app.cell
def _(mo, node_total):
    def _save(*args,**kwargs):
        with mo.status.spinner("Saving `node_total` to `node_total.csv.gz`"):
            node_total.round(3).to_csv("node_total.csv.gz",index=True,header=True,compression="gzip")

    _save_ui = mo.ui.button(label="Save `node_total` to `node_total.csv.gz`",on_click=_save)
    _save_ui
    return


@app.cell
def _():
    import datetime as dt
    import marimo as mo
    import pandas as pd
    from fips import Counties

    return Counties, dt, mo, pd


if __name__ == "__main__":
    app.run()
