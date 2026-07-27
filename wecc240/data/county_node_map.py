import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook reviews the county to node mapping in `county_node_map.csv`.
    """)
    return


@app.cell
def _(read_county_node_map, read_states):
    states = read_states()
    county_node_map = read_county_node_map().set_index("county_st")
    return county_node_map, states


@app.cell
def _(county_node_map, mo, states):
    _tabs = {}
    for _state in states:
        _counties = [x for x in county_node_map.index if x.endswith(_state)]
        _tabs[_state] = mo.ui.table(county_node_map.loc[_counties],selection=None,page_size=min(60,len(_counties)))
    mo.ui.tabs(_tabs)
    return


@app.cell
def _(help_md, mo, read_county_node_map):
    mo.accordion(help_md(read_county_node_map))
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    from wecc240_data import read_states, read_county_node_map, help_md

    return help_md, mo, read_county_node_map, read_states


if __name__ == "__main__":
    app.run()
