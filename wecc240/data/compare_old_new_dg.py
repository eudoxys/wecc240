import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(r"""
    This notebook compares the old and new DG dataset
    """)
    return


@app.cell
def _(mo):
    raw_ui = mo.ui.checkbox(label="Use raw old data.")
    return (raw_ui,)


@app.cell
def _(mo, new, old, raw_ui):
    _common = sorted(set(old.columns) & set(new.columns))
    _diff = (set(old.columns)|set(new.columns)) - set(_common)
    n_columns = 6
    column_groups = {
        f"{_common[x]} - {_common[min(x+n_columns-1,len(_common)-1)]}": _common[
            x : min(x + n_columns - 1, len(_common) - 1)
        ]
        for x in range(0, len(_common), n_columns)
    }

    column_ui = mo.ui.dropdown(
        options=column_groups, value=list(column_groups)[0], label="Nodes range:"
    )
    mo.hstack([raw_ui,mo.md("") if len(old.columns) == len(new.columns) and (old.columns == new.columns).all() else mo.md(f"**<font color=red>WARNING: Columns differ: {_diff}</font>**")],justify='start')
    return (column_ui,)


@app.cell
def _(mo, old):
    date_ui = mo.ui.date_range(
        start=min(old.index).strftime("%Y-%m-%d"),
        stop=max(old.index).strftime("%Y-%m-%d"),
        value=["2020-08-01", "2020-08-31"],
        label="Date range:",
    )
    return (date_ui,)


@app.cell
def _(mo):
    total_ui = mo.ui.dropdown(label="Total", options=["Node range", "All nodes"])
    return (total_ui,)


@app.cell
def _(mo, pd, raw_ui):
    with mo.status.spinner("Loading old data"):
        _oldname = "aggregate_node_distributed_solar_production.csv.gz" if raw_ui.value else "node_dg.csv.gz"
        old = (
            pd.read_csv(_oldname, index_col=[0], parse_dates=[0])
            .resample("1h")
            .mean()
            .rename_axis("timestamp")
        )
        old.columns = [x.split("_")[0] for x in sorted(old.columns)]
    return (old,)


@app.cell
def _(mo, pd):
    with mo.status.spinner("Loading new data"):
        new = (
            pd.read_csv(
                "residential_solar_geopanel.csv.gz", index_col=[0], parse_dates=[0]
            )
            .resample("1h")
            .mean()
            .rename_axis("timestamp")
        )
        new.columns = sorted(new.columns)
    return (new,)


@app.cell
def _(column_ui, date_ui, mo, total_ui):
    mo.hstack([column_ui,date_ui,total_ui])
    return


@app.cell
def _(column_ui, date_ui, mo, new, old, pd, plt, total_ui):
    _dates = pd.date_range(
        start=date_ui.value[0].strftime("%Y-%m-%d 00:00:00+0000"),
        end=date_ui.value[1].strftime("%Y-%m-%d 23:59:50+0000"),
        freq="1h",
    )

    _old, _new = (
        old.loc[_dates, column_ui.value] / 1e3,
        new.loc[_dates, column_ui.value] / 1e3,
    )
    match total_ui.value:
        case "Node range":
            _old, _new = (
                old.loc[_dates, column_ui.value].sum(axis=1) / 1e3,
                new.loc[_dates, column_ui.value].sum(axis=1) / 1e3,
            )
        case "All nodes":
            _old, _new = (
                old.loc[_dates, :].sum(axis=1) / 1e3,
                new.loc[_dates, :].sum(axis=1) / 1e3,
            )
    _diff = _new - _old
    _pcdiff = _diff / _old * 100

    _options = dict(figsize=(10, 7), grid=True, xlabel="Date/Time")
    plt.close()
    _oldplt = _old.plot(**_options, ylabel="Power (MW)", title="Old DG").figure
    plt.close()
    _newplt = _new.plot(**_options, ylabel="Power (MW)", title="New DG").figure
    plt.close()
    _diffplt = _diff.plot(
        **_options, ylabel="Power (MW)", title="DG Change"
    ).figure
    plt.close()
    _pcdiffplt = _pcdiff.plot(
        **_options, ylabel="Power (%)", title="DG Change"
    ).figure

    mo.ui.tabs(
        {
            "Old DG (MW)": mo.ui.tabs(
                {"Plot": _oldplt, "Data": _old.round(1)}, lazy=True
            ),
            "New DG (MW)": mo.ui.tabs(
                {"Plot": _newplt, "Data": _new.round(1)}, lazy=True
            ),
            "Diff (MW)": mo.ui.tabs(
                {"Plot": _diffplt, "Data": _diff.round(1)}, lazy=True
            ),
            "Diff (%)": mo.ui.tabs(
                {"Plot": _pcdiffplt, "Data": _pcdiff.round(1)}, lazy=True
            ),
        },
        lazy=True,
    )
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    return mo, pd, plt


if __name__ == "__main__":
    app.run()
