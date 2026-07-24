import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook tests the total load calibration solution.
    """)
    return


@app.cell(hide_code=True)
def _(mo, month_ui, year_ui):
    mo.md(rf"""
    The total load data is downloaded from the [wecc240 load data](https://github.com/eudoxys/wecc240/tree/main/wecc240/data) for {month_ui} {year_ui} data.
    """)
    return


@app.cell
def _(ba_ui, mo, normalize_ui):
    # Show normalization UI
    mo.hstack([ba_ui,normalize_ui,mo.accordion({"ℹ️ ":"Select with balancing authority (BA) from which to select nodes. Normalization controls whether the data tables and plot are normalized to the peak load. It does not effect the results"})])
    return


@app.cell
def _(data, mo, normalize_ui, peak, plot_ui, result_ui, units):
    # Show main UI
    _scale = 1/peak if normalize_ui.value else 1e-3
    mo.accordion(
        {
            "Data": (data*_scale).round(3),
            "Plot": mo.mpl.interactive(
                (data*_scale).plot(
                    kind='area',
                    legend=False,
                    figsize=(10, 7),
                    grid=True,
                    ylabel=f"Power ({units})",
                    title=f"Total energy: {data.sum(axis=None)/1e6:.2f} TWh / Peak power: {data.sum(axis=1).max()/1e3:.3f} GW",
                )
            ),
            "Solution":plot_ui,
            "Results":result_ui,
        },multiple=True
    )
    return


@app.cell
def _(bus_gis, clear_results, mo):
    # UI elements
    ba_ui = mo.ui.multiselect(options=bus_gis["BA"].unique(),label="Balancing authority:")
    month_ui = mo.ui.dropdown(options={
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    },value="August")
    year_ui = mo.ui.dropdown(options=range(2018,2023),value=2020)
    normalize_ui = mo.ui.checkbox(label="Normalize data tables and plots")
    energy_ui = mo.ui.slider(
        label="Energy: ",
        start=0.1,
        stop=2.0,
        step=0.1,
        value=1.1,
        show_value=True,
    )
    power_ui = mo.ui.slider(
        label="Power: ",
        start=0.1,
        stop=2.0,
        step=0.1,
        value=0.7,
        show_value=True,
    )
    gamma_options = [10**n for n in range(0,6)]
    gamma_ui = mo.ui.slider(
        label=r"$\gamma$",
        steps=gamma_options,
        value=1000,
        show_value=True,
    )
    mu_options = [0] + sorted([x*y for x in [1,2,5] for y in [10**n for n in range(-2,3)]])
    mu_ui = mo.ui.slider(
        label=r"$\mu$: ",
        steps=mu_options,
        value=1.0,
        show_value=True,
    )
    lambda_options = [0] + [10**n for n in range(-3,3)]
    lambda_ui = mo.ui.slider(
        label=r"$\lambda$: ",
        steps=lambda_options,
        value=0.0,
        show_value=True,
    )
    epsilon_options = [10**n for n in range(-6,1)]
    epsilon_ui = mo.ui.slider(
        label=r"$\epsilon$",
        steps=epsilon_options,
        value=1e-3,
        show_value=True,
    )
    target_ui = mo.hstack(
        [
            mo.vstack(
                [
                    mo.hstack([energy_ui, power_ui, gamma_ui], justify="start"),
                    mo.hstack([mu_ui, lambda_ui,epsilon_ui], justify="start"),
                ],
            ),
            mo.accordion(
                {
                    "ℹ️": "The target energy and power are factors applied to original data, i.e., 1.1 is a 10% increase. The $\gamma$ parameters is the primary regularized and prevents crushing of the output. The $\mu$ parameter controls the total energy fidelity to the energy total. The $\lambda$ parameter drives the peak power to the power target. The $\epsilon$ parameter is the symmetric well-posedness ridge."
                }
            ),
        ],
        justify="start",
    )
    score_ui = mo.ui.slider(label="Power error score weight (per unit energy error):",steps=[0,0.1,0.2,0.5,1.0,2.0,5.0,10,1e6],value=2.0,show_value=True)
    clear_ui = mo.ui.button(label="Clear results",on_click=clear_results)
    return (
        ba_ui,
        clear_ui,
        energy_ui,
        epsilon_ui,
        gamma_ui,
        lambda_ui,
        month_ui,
        mu_options,
        mu_ui,
        normalize_ui,
        power_ui,
        target_ui,
        year_ui,
    )


@app.cell
def _(
    clear_ui,
    get_history,
    mo,
    mu_options,
    pd,
    plot_results,
    problem,
    sweep_ui,
    target_ui,
):
    # Display history of results
    plot_ui = mo.vstack([target_ui,plot_results(problem)])
    _results = (
        pd.DataFrame(
            data=get_history().values(),
            index=get_history().keys(),
            columns=[
                "BA",
                "Y/M",
                "E",
                "P",
                "γ",
                "μ",
                "λ",
                "ε",
                "Eerr (%)",
                "Perr (%)",
                "Score",
            ],
        )
        .reset_index(drop=True)
        .set_index(["BA","Y/M","E", "P","γ","μ","λ","ε"])
    )
    result_ui = mo.vstack(
        [
            mo.ui.table(
                _results.round(6).sort_values(["BA","Y/M","Perr (%)","Score","Eerr (%)"]),
                selection=None,page_size=len(mu_options)
            ),
            mo.hstack([
                # score_ui, 
                sweep_ui,
                clear_ui, 
            ]),
        ]
    )
    return plot_ui, result_ui


@app.cell
def _():
    #
    # Single-shot solution update
    #
    return


@app.cell
def _(E, P, X, epsilon_ui, gamma_ui, lambda_ui, mu_ui, solution):
    # Obtain the solution to the problem
    cost, problem = solution(
        X,
        E,
        P,
        gamma=gamma_ui.value,
        lam=lambda_ui.value,
        mu=mu_ui.value,
        eps=epsilon_ui.value,
    )
    return (problem,)


@app.cell
def _():
    #
    # Support Functions
    #
    return


@app.cell
def _(np):
    # Compute the output based on the input
    def forward(X: np.array, scale: np.array, offset: np.array):
        assert X.shape[1] == len(scale)
        assert X.shape[1] == len(offset)
        return X * scale + offset

    return (forward,)


@app.cell
def _(np):
    # Compute the inputs based on the output (not actually used)
    def backward(Y: np.array, scale: np.array, offset: np.array):
        assert Y.shape[1] == len(scale)
        assert Y.shape[1] == len(offset)
        return (Y - offset) / scale

    return


@app.function
# Read scalar constants from problem data
def get_scalar(problem,name):
    """Read scalar from problem data"""
    for const in problem.constants():
        if const.name() == name:
            return float(const.value)
    raise ValueError(f"{name=} not found")


@app.function
# Read variable values from problem data
def get_variable(problem,name):
    """Read variable from problem data"""
    for var in problem.variables():
        if var.name() == name:
            return var.value


@app.cell
def _(mo):
    # Record history of results
    get_history, set_history = mo.state({})

    def clear_results(*args, **kwargs):
        set_history({})

    def record_result(*data):
        result_history = get_history()
        result_history[",".join(str(x) for x in data)] = data
        set_history(result_history)

    return clear_results, get_history, record_result


@app.cell
def _(X, ba_ui, forward, month_ui, np, record_result, year_ui):
    def get_results(problem):
        """Calculate and record results of problem solve"""
        s = get_variable(problem,"s")
        b = get_variable(problem,"b")

        Y = forward(X, s, b)

        E = get_scalar(problem,"E")
        P = get_scalar(problem,"P")

        energy_ferr = 1 - Y.sum() / E
        power_ferr = 1 - Y.sum(axis=1).max() / P
        score = np.sqrt(np.sum((Y-X)**2))

        record_result(
            "|".join(ba_ui.value) if ba_ui.value else "WECC",
            f"{year_ui.value:04d}-{month_ui.value:02d}",
            round(E / X.sum(), 1),
            round(P, 1),
            round(get_scalar(problem,"gamma"), 4),
            round(get_scalar(problem,"mu"), 4),
            round(get_scalar(problem,"lam"), 4),
            round(get_scalar(problem,"eps"), 4),
            round(abs(energy_ferr*100), 2),
            round(abs(power_ferr*100), 2),
            round(score, 3),
        )
        return Y, energy_ferr, power_ferr

    return (get_results,)


@app.cell
def _(
    E,
    P,
    X,
    epsilon_ui,
    gamma_ui,
    get_results,
    lambda_ui,
    mo,
    mu_options,
    problem,
    solution,
):
    # Sweep values of my and record solution results
    def sweep_mu(*args, **kwargs):
        with mo.status.progress_bar(
            title="Sweeping values of mu",
            total=len(mu_options),
            remove_on_exit=True,
        ) as _bar:
            for mu in mu_options:
                _bar.update(subtitle=f"Solving {mu=}")
                get_results(
                    solution(
                        X,
                        E,
                        P,
                        gamma=gamma_ui.value,
                        mu=mu,
                        lam=lambda_ui.value,
                        eps=epsilon_ui.value,
                    )[1]
                )

    sweep_ui = mo.hstack(
        [
            mo.ui.button(label=r"Sweep $\mu$", on_click=sweep_mu),
            mo.md(
                f"with $\lambda={get_scalar(problem, 'lam'):.3f}$, $\gamma={get_scalar(problem, 'gamma'):.3f}$, and $\epsilon={get_scalar(problem, 'eps')}$"
            ),
        ],
        justify="start",
    )
    return (sweep_ui,)


@app.cell
def _(
    X,
    data,
    energy_ui,
    get_results,
    mo,
    normalize_ui,
    pd,
    peak,
    plt,
    power_ui,
    units,
):
    # Generate plot of results
    def plot_results(problem):
        """Generate plot of results"""
        if problem.status not in ("infeasible", "unbounded"):

            Y, energy_ferr, power_ferr = get_results(problem)
            _plotscale = 1 if normalize_ui.value else peak / 1e3

            plt.close()

            pd.DataFrame(
                data={
                    "Original": X.max(axis=0) * _plotscale,
                    "Rescaled": Y.max(axis=0) * _plotscale,
                },
                index=data.columns,
            ).plot(
                kind="bar",
                grid=True,
                figsize=(11, 7),
                ylabel=f"Power ({units})",
            )
            plt.title(
                f"""Energy target: {energy_ui.value*data.sum(axis=None)/1e6:.2f} TWh / Power target: {power_ui.value*data.sum(axis=1).max()/1e3:.3f} GW
    Solution status: {problem.status.title().replace('_', ' ')}
    Energy error: {energy_ferr * 100:.2f}% / Power error: {power_ferr * 100:.2f}%"""
            )
            plt.legend()
            plt.xticks(rotation=90)
            _result = plot_2 = plt.gca()
        else:
            _result = mo.md(
                f"**<font color=red>ERROR: {problem.status}</font>**"
            )
        return _result

    return (plot_results,)


@app.cell
def _():
    #
    # Data loading
    #
    return


@app.cell
def _(mo, pd):
    # Load data
    with mo.status.spinner("Reading node load data"):
        node_total = pd.read_csv("https://raw.githubusercontent.com/eudoxys/wecc240/refs/heads/main/wecc240/data/node_total.csv", index_col=[0], parse_dates=[0])
    return (node_total,)


@app.cell
def _(date_range, energy_ui, node_total, nodes, normalize_ui, power_ui):
    # Data setup for problem
    data = node_total.loc[date_range, sorted(nodes)].rename_axis(
        "timestamp"
    )
    X = data.values
    peak = X.sum(axis=1).max()
    # peak = X.max()
    units = "pu.peak MW" if normalize_ui.value else "GW"
    X /= peak
    P = float(X.sum(axis=1).max()) * power_ui.value
    E = float(X.sum(axis=None)) * energy_ui.value
    return E, P, X, data, peak, units


@app.cell
def _(mo, pd):
    # GIS data
    with mo.status.spinner("Reading bus GIS data"):
        bus_gis = pd.read_csv("https://raw.githubusercontent.com/eudoxys/wecc240/refs/heads/main/wecc240/data/bus_gis.csv")
        load_bus = bus_gis[bus_gis["LOAD"] > 0]

    return bus_gis, load_bus


@app.cell
def _(ba_ui, bus_gis, load_bus, node_total):
    _ba = ba_ui.value if ba_ui.value else bus_gis["BA"]
    nodes = [
        x
        for x in load_bus.set_index("BA").loc[_ba, "GEOHASH"].unique()
        if x in node_total.columns
    ]
    return (nodes,)


@app.cell
def _(cal, month_ui, pd, year_ui):
    # Date range
    _year = year_ui.value
    _month = month_ui.value
    date_range = pd.date_range(
        start=f"{_year}-{_month:02d}-01 00:00:00+0000",
        end=f"{_year}-{_month:02d}-{cal.monthrange(_year,_month)[1]} 23:00:00+0000",
        freq="1h")
    return (date_range,)


@app.cell
def _():
    # import
    import marimo as mo
    import calendar as cal
    import numpy as np
    import pandas as pd
    import cvxpy as cp
    import matplotlib.pyplot as plt
    from node_calibrate import cvx_options, _solver as solution

    return cal, mo, np, pd, plt, solution


if __name__ == "__main__":
    app.run()
