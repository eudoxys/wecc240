import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook reviews the state-level monthly energy production and consumption as reported by EIA and saved in the local file `state_mwh.csv`.
    """)
    return


@app.cell
def _(mo, read_states):
    states = read_states()
    state_ui = mo.ui.dropdown(options=states,label="State:")
    return (state_ui,)


@app.cell
def _(mo, read_state_mwh, state_ui):
    state_mwh = read_state_mwh().set_index("state",append=True)
    if state_ui.value is None:
        _df = state_mwh.groupby("timestamp").sum()/1e6
    else:
        _df = state_mwh.groupby(["state","timestamp"]).sum().loc[state_ui.value]/1e6
    _df.columns = [x for x in _df.columns]

    _plt = _df.plot(
        figsize=(10, 7),
        grid=True,
        ylabel="Monthly energy (TWh)",
        xlabel="Date/Time (UTC)",
        title="EIA Monthly Energy",
    )
    mo.ui.tabs({
     "Data": mo.vstack([state_ui,mo.ui.table(_df.round(3),selection=None,page_size=12)]),
     "Plot": mo.vstack([state_ui,mo.mpl.interactive(_plt)]),
    })
    return


@app.cell
def _(help_md, mo, read_state_mwh, read_states):
    mo.accordion(help_md([read_states,read_state_mwh]))
    return


@app.cell
def _():
    import marimo as mo
    from wecc240_data import read_state_mwh, read_states, help_md
    import datetime as dt
    import pandas as pd
    from eia import Form923, Form861m, HS861m
    from fips import Counties

    return help_md, mo, read_state_mwh, read_states


if __name__ == "__main__":
    app.run()
