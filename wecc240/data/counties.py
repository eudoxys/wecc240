import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook reviews the counties data.
    """)
    return


@app.cell
def _(mo, read_counties, read_states):
    states = read_states()
    counties = read_counties().set_index(["ST","COUNTY"])
    counties_ui = mo.ui.tabs({x:counties.loc[x] for x in states})
    return (counties_ui,)


@app.cell
def _(counties_ui):
    counties_ui
    return


@app.cell
def _(help_md, mo, read_counties, read_states):
    mo.accordion({x:mo.md(y) for x,y in help_md([read_counties,read_states]).items()})
    return


@app.cell
def _(mo, read_counties, read_states):
    mo.accordion({"Help":mo.md(read_counties.__doc__ + "\n----\n" + read_states.__doc__)})
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    from wecc240_data import read_counties, read_states, help_md

    return help_md, mo, read_counties, read_states


if __name__ == "__main__":
    app.run()
