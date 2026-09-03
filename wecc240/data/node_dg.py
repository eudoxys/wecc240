import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook review the `node_dg` imported from the NLR aggregate solar DG data.
    """)
    return


@app.cell
def _(read_bus_gis, read_node_dg):
    node_dg = read_node_dg().set_index("timestamp")
    bus_gis = read_bus_gis().set_index("GEOHASH")
    return bus_gis, node_dg


@app.cell
def _(bus_gis, mo, node_dg, plt):
    def options(_nodes, _step):
        return {
            f"{_nodes[x]} $-$ {_nodes[min(x + _step, len(_nodes)) - 1]}": _nodes[
                x : min(x + _step, len(_nodes))
            ]
            for x in range(0, len(_nodes), _step)
        }

    with mo.status.progress_bar(
        title="Generating plots",
        total=len(node_dg.columns),
        remove_on_exit=True,
    ) as _bar:
        _plot = {}
        _options = dict(
            figsize=(10, 7),
            grid=True,
            xlabel="Date/Time (UTC)",
            ylabel="Power (MW)",
        )
        for _column in node_dg.columns:
            _bar.update(subtitle=_column)
            plt.close()
            _plot[_column] = node_dg[_column].plot(
                title=f"{bus_gis['NAME'].to_dict()[_column]} ({_column})",
                **_options,
            )

    _step = 7  # number of columns per tab
    mo.ui.tabs(
        {
            x: mo.ui.tabs(
                {
                    "Plot": mo.ui.tabs(
                        {
                            bus_gis["NAME"].to_dict()[z]: mo.mpl.interactive(
                                _plot[z]
                            )
                            for z in y
                        }
                    ),
                    "Data": mo.ui.table(
                        node_dg[y], selection=None, page_size=24
                    ),
                },
                lazy=True,
            )
            for x, y in options(node_dg.columns, _step).items()
        },
        lazy=True,
    )
    return


@app.cell
def _(help_md, mo, read_node_dg):
    mo.accordion(help_md(read_node_dg))
    return


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    from wecc240_data import read_node_dg, read_bus_gis, help_md

    return help_md, mo, plt, read_bus_gis, read_node_dg


if __name__ == "__main__":
    app.run()
