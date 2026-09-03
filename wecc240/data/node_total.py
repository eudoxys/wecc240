import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook reviews the `node_total.csv` data.
    """)
    return


@app.cell
def _(read_bus_gis, read_node_total):
    data = read_node_total().set_index("timestamp")
    bus_gis = read_bus_gis().set_index("GEOHASH")
    return bus_gis, data


@app.cell
def _(bus_gis, data, mo, plt):
    def options(_nodes, _step):
        return {
            f"{_nodes[x]} $-$ {_nodes[min(x + _step, len(_nodes)) - 1]}": _nodes[
                x : min(x + _step, len(_nodes))
            ]
            for x in range(0, len(_nodes), _step)
        }

    with mo.status.progress_bar(
        title="Generating plots",
        total=len(data.columns),
        remove_on_exit=True,
    ) as _bar:
        _plot = {}
        _options = dict(
            figsize=(10, 7),
            grid=True,
            xlabel="Date/Time (UTC)",
            ylabel="Power (MW)",
        )
        for _column in data.columns:
            _bar.update(subtitle=_column)
            plt.close()
            _plot[_column] = data[_column].plot(
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
                        data[y], selection=None, page_size=24
                    ),
                },
                lazy=True,
            )
            for x, y in options(data.columns, _step).items()
        },
        lazy=True,
    )
    return


@app.cell
def _(help_md, mo, read_node_total):
    mo.accordion(help_md(read_node_total))
    return


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    from wecc240_data import read_node_total, read_bus_gis, help_md

    return help_md, mo, plt, read_bus_gis, read_node_total


if __name__ == "__main__":
    app.run()
