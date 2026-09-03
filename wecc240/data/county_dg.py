import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook reviews the `county_dg.csv` data:
    """)
    return


@app.cell
def _(mo, read_county_dg):
    data = read_county_dg().set_index("timestamp")
    states = sorted(set([x.split(" ")[-1] for x in data.columns]))
    counties = {x:[] for x in states}
    for _county in data.columns:
        _state = _county.split(" ")[-1]
        counties[_state].append(" ".join(_county.split(" ")[:-1]))
        state_ui = mo.ui.tabs(
        {x:mo.md("") for x in states}
    )
    state_ui
    return counties, data, state_ui


@app.cell
def _(counties, data, mo, plt, state_ui):
    _plots = {}
    _options = dict(figsize=(10,7),grid=True,xlabel="Date/Time (UTC)",ylabel="Power (MW)")
    with mo.status.progress_bar(title="Generating plots...",total=len(counties[state_ui.value]),remove_on_exit=True) as _bar:
        for _county in counties[state_ui.value]:
            plt.close()
            _county_st = f"{_county} {state_ui.value}"
            _bar.update(subtitle=_county_st)
            _plots[_county] = mo.mpl.interactive(data[_county_st].plot(**_options,title=_county_st))
    _plot_ui = mo.ui.tabs(_plots)
    _data_ui = data[[x for x in data.columns if x.endswith(state_ui.value)]].round(3)
    mo.ui.tabs({
        "Plot":_plot_ui,
        "Data":_data_ui,
    })
    return


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    from wecc240_data import read_county_dg, help_md

    return mo, plt, read_county_dg


if __name__ == "__main__":
    app.run()
