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
def _(mo, normalize_ui):
    # Show normalization UI
    mo.hstack([normalize_ui,mo.accordion({"ℹ️ ":"This controls whether the data tables and plot are normalized to the peak load. It does not effect the results"})],justify="start")
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
                    legend=False,
                    figsize=(10, 7),
                    grid=True,
                    ylabel=f"Power ({units})",
                    title="Node power",
                )
            ),
            "Solution":plot_ui,
            "Results":result_ui,
        },multiple=True
    )
    return


@app.cell
def _(mo):
    # Date selection
    month_ui = mo.ui.dropdown(options={
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    },value="August")
    year_ui = mo.ui.dropdown(options=range(2018,2023),value=2020)
    return month_ui, year_ui


@app.cell
def _(month_ui, pd, year_ui):
    # Date range
    date_range = pd.date_range(
        start=f"{year_ui.value}-{month_ui.value:02d}-01 00:00:00+0000",
        end=f"{year_ui.value}-{month_ui.value:02d}-31 23:00:00+0000",
        freq="1h")
    return (date_range,)


@app.cell
def _(mo, pd):
    # Load data
    with mo.status.spinner("Reading node load data"):
        node_total = pd.read_csv("https://raw.githubusercontent.com/eudoxys/wecc240/refs/heads/main/wecc240/data/node_total.csv", index_col=[0], parse_dates=[0])
    return (node_total,)


@app.cell
def _(mo, node_total, pd):
    # GIS data
    with mo.status.spinner("Reading bus GIS data"):
        bus_gis = pd.read_csv("https://raw.githubusercontent.com/eudoxys/wecc240/refs/heads/main/wecc240/data/bus_gis.csv")
        load_bus = bus_gis[bus_gis["LOAD"] > 0]
        nodes = [
            x
            for x in load_bus.set_index("BA").loc["CA", "GEOHASH"].unique()
            if x in node_total.columns
        ]
    return (nodes,)


@app.cell
def _(date_range, energy_ui, node_total, nodes, normalize_ui, power_ui):
    # Data setup for problem
    data = node_total.loc[date_range, sorted(nodes)].rename_axis(
        "timestamp"
    )
    X = data.values
    peak = X.max()
    units = "pu.peak MW" if normalize_ui.value else "GW"
    X /= peak
    P = float(X.sum(axis=1).max()) * power_ui.value
    E = float(X.sum(axis=None)) * energy_ui.value
    return E, P, X, data, peak, units


@app.cell
def _(clear_results, mo):
    # UI elements
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
        value=0.9,
        show_value=True,
    )
    lambda_ui = mo.ui.slider(
        label=r"$\lambda$: ",
        start=0,
        stop=10,
        step=0.1,
        value=1.8,
        debounce=True,
        show_value=True,
    )
    mu_ui = mo.ui.slider(
        label=r"$\mu$: ",
        start=0,
        stop=20,
        step=0.1,
        value=2.3,
        debounce=True,
        show_value=True,
    )
    target_ui = mo.hstack(
        [
            mo.vstack(
                [
                    mo.hstack([energy_ui, power_ui], justify="start"),
                    mo.hstack([lambda_ui, mu_ui], justify="start"),
                ],
            ),
            mo.accordion(
                {
                    "ℹ️": "The target energy and power are factors applied to original data, i.e., 1.1 is a 10% increase. The $\lambda$ parameter drives the peak power to the power target, and the $\mu$ parameter controls the total energy fidelity to the energy total."
                }
            ),
        ],
        justify="start",
    )
    score_ui = mo.ui.slider(label="Power error score weight (per unit energy error):",steps=[0,0.1,0.2,0.5,1.0,2.0,5.0,10,1e6],value=2.0,show_value=True)
    clear_ui = mo.ui.button(label="Clear results",on_click=clear_results)
    return (
        clear_ui,
        energy_ui,
        lambda_ui,
        mu_ui,
        normalize_ui,
        power_ui,
        score_ui,
        target_ui,
    )


@app.cell
def _(E, P, X, lambda_ui, mu_ui, solution):
    # Obtain the solution to the problem
    _,problem = solution(X, P, E,lam=lambda_ui.value,mu=mu_ui.value)
    return (problem,)


@app.cell
def _(mo, plot_results, problem, target_ui):
    # Generation the plot element
    plot_ui = mo.vstack([target_ui,plot_results(problem)])
    return (plot_ui,)


@app.cell
def _(cp, np):
    # Setup and solve the problem
    def solution(X:np.array,
                   P_target:float,
                   E_target:float,
                   *,
                   lam:float=1.0,
                   mu:float=1.0,
                   eps:float=1e-3,
                   options:dict=cvx_options(),
                  ):
        """Solve the single energy/power target using scale only

        Arguments
        ---------
        - `X(T, n)`: nonnegative array of time-series signals
        - `E_target`: scalar energy target
        - `P_target`: scalar power target
        - `lam`: power target objective hyperparameter (presses peak to ceiling)
        - `mu`: energy target objective hyperparameter (recovers energy equality)   
        - `eps`: small symmetric redice guaranteed a unique solution when zero or constant columns are present
        """
        T, n = X.shape

        a = cp.Constant(X.sum(axis=0),name='a')     # column energy weights, shape (n,)

        E = cp.Constant(E_target,name='E')
        P = cp.Constant(P_target,name='P')

        s = cp.Variable(n, nonneg=True, name='s')
        b = cp.Variable(n, name='b')

        peak = cp.max(X @ s) + cp.sum(b)            # convex expression
        energy = a @ s + T * cp.sum(b)              # affine
        energy_residual = energy - E_target         # affine
        constraints = [
            peak <= P,                              # power inequality (convex relaxation)
        ]
        objective = cp.Minimize(
            cp.sum_squares(s - 1) 
            + mu * cp.sum_squares(energy_residual/T)
            - lam * cp.sum(b) 
        )

        prob = cp.Problem(objective, constraints)
        result = prob.solve(**options)

        if prob.status not in ("infeasible", "unbounded"):
            scale = s.value.round(4)
            offset = b.value.round(3)
            print("scaling factors:", scale)
            print("power offset:", offset)
            print("achieved energy:", (a @ s + T*b).value, " target:", E.value)
            print("achieved power :", (cp.max(X@s,axis=0) + b).value, " target:", P.value)
        else:
            print("Problem status:", prob.status)

        return result,prob

    return (solution,)


@app.cell
def _(np):
    # Compute the output based on the input
    def forward(X:np.array,scale:np.array,offset:np.array):
        assert X.shape[1] == len(scale)
        assert X.shape[1] == len(offset)
        return X * scale + offset

    return (forward,)


@app.cell
def _(np):
    # Compute the inputs based on the output (not actually used)
    def backward(Y:np.array,scale:np.array,offset:np.array):
        assert Y.shape[1] == len(scale)
        assert Y.shape[1] == len(offset)
        return (Y-offset) / scale

    return


@app.cell
def _(mo):
    # Record history of results
    get_history,set_history = mo.state({})
    def clear_results(*args,**kwargs):
        set_history({})
    def record_result(Y,energy,power,lmbd,mu,energy_ferr,power_ferr):
        data = [energy,power,lmbd,mu,energy_ferr,power_ferr]
        result_history = get_history()
        result_history[",".join(f"{x:.1f}" for x in data)] = data
        set_history(result_history)

    return clear_results, get_history, record_result


@app.cell
def _(clear_ui, get_history, mo, pd, plot_ui, score_ui):
    # Display history of results
    plot_ui
    _results = (
        pd.DataFrame(
            data=get_history().values(),
            index=get_history().keys(),
            columns=[
                "Energy target",
                "Power target",
                "λ",
                "μ",
                "Energy error (%)",
                "Power error (%)",
            ],
        )
        .abs()
        .reset_index(drop=True)
        .set_index(["Energy target", "Power target", "λ", "μ"])
    )
    _results["Score"] = (
        (min(score_ui.value,1) * _results["Energy error (%)"] + max(score_ui.value,1) * _results["Power error (%)"]) / max(score_ui.value,1)
    )
    result_ui = mo.vstack(
        [
            mo.hstack([score_ui,clear_ui]),
            mo.ui.table(
                (_results * 100).round(2).sort_values("Score"),
                selection=None,
            ),
        ]
    )
    return (result_ui,)


@app.function
def errors(Y,E,P):
    energy_ferr = 1 - Y.sum() / E
    power_ferr = 1 - Y.sum(axis=1).max() / P
    return energy_ferr,power_ferr


@app.cell
def _(
    E,
    P,
    X,
    data,
    energy_ui,
    forward,
    lambda_ui,
    mo,
    mu_ui,
    normalize_ui,
    pd,
    peak,
    plt,
    power_ui,
    record_result,
    units,
):
    # Generate plot of results
    def plot_results(_problem):
        if _problem.status not in ("infeasible", "unbounded"):
            scale = _problem.variables()[0].value
            offset = _problem.variables()[1].value
            Y = forward(X, scale, offset)

            energy_ferr,power_ferr = errors(Y,E,P)
            record_result(Y,energy_ui.value,power_ui.value,lambda_ui.value,mu_ui.value,energy_ferr,power_ferr)
            _plotscale = 1 if normalize_ui.value else peak/1e3

            plt.close()

            pd.DataFrame(
                data={
                    "Original": X.max(axis=0) * _plotscale,
                    "Rescaled": Y.max(axis=0) * _plotscale,
                },
                index=data.columns,
            ).plot(kind="bar", grid=True, figsize=(11, 7), ylabel=f"Power ({units})")
            plt.title(
                f"Energy target: {energy_ui.value} / Power target: {power_ui.value} \n Solution status: {_problem.status.title().replace('_', ' ')} \n Energy error: {energy_ferr * 100:.2f}% / Power error: {power_ferr * 100:.2f}%"
            )
            plt.legend()
            plt.xticks(rotation=90)
            _result = plot_2 = plt.gca()
        else:
            _result = mo.md(
                f"**<font color=red>ERROR: {_problem.status}</font>**"
            )
        return _result

    return (plot_results,)


@app.function
# Set the default cvxpy solve options
def cvx_options(**kwargs):
    """Specify default cvxs problem options"""
    options = {
        "solver": "clarabel",
        "verbose": True,
    }
    options.update(kwargs)
    return options


@app.cell
def _():
    # import
    import marimo as mo
    import numpy as np
    import pandas as pd
    import cvxpy as cp
    import matplotlib.pyplot as plt

    return cp, mo, np, pd, plt


if __name__ == "__main__":
    app.run()
