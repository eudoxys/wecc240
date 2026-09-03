import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook reviews the `bus_gis.csv` data from the WECC GIS data.
    """)
    return


@app.cell
def _(read_bus_gis):
    bus_gis = read_bus_gis()
    return (bus_gis,)


@app.cell
def _(bus_gis, mo):
    mo.ui.table(bus_gis,selection=None,page_size=27)
    return


@app.cell
def _(help_md, mo, read_bus_gis):
    mo.accordion(help_md(read_bus_gis))
    return


@app.cell
def _():
    import marimo as mo
    from wecc240_data import read_bus_gis, help_md

    return help_md, mo, read_bus_gis


if __name__ == "__main__":
    app.run()
