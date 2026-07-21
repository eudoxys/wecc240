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
def _(mo):
    mo.md(r"""
    # Data

    The original load data is taken from wecc240 load model using the August 2020 data.
    """)
    return


@app.cell
def _(pd):
    node_total = pd.read_csv("node_total.csv", index_col=[0], parse_dates=[0])
    return (node_total,)


@app.cell
def _(pd):
    date_range = pd.date_range(
        start="2020-08-01 00:00:00+0000",
        end="2020-08-31 23:00:00+0000",
        freq="1h")
    return (date_range,)


@app.cell
def _(node_total, pd):
    bus_gis = pd.read_csv("bus_gis.csv")
    load_bus = bus_gis[bus_gis["LOAD"] > 0]
    caiso_nodes = [
        x
        for x in load_bus.set_index("BA").loc["CA", "GEOHASH"].unique()
        if x in node_total.columns
    ]
    return (caiso_nodes,)


@app.cell
def _(caiso_nodes, date_range, energy_ui, mo, node_total, power_ui):
    data = node_total.loc[date_range, sorted(caiso_nodes)].rename_axis(
        "timestamp"
    )
    X = data.values
    X /= X.max()
    P = float(X.sum(axis=1).max()) * power_ui.value
    E = float(X.sum(axis=None)) * energy_ui.value
    mo.accordion(
        {
            "Plot": mo.mpl.interactive(
                (data/data.max(axis=None)).plot(
                    legend=False,
                    figsize=(10, 7),
                    grid=True,
                    ylabel="Power (pu.MW peak)",
                    title="Node power",
                )
            ),
            "Data": (data/data.max(axis=None)).round(3),
        }
    )
    return E, P, X, data


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Single region

    This simplest problem is a set of multiple nodes within a single region with an energy and power target pair. The data is normalized w.r.t to the peak value.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The following setup the target power and energy to achieve.
    """)
    return


@app.cell
def _(mo):
    power_ui = mo.ui.slider(label="Power target: ",start=0.1,stop=2.0,step=0.1,value=1.2,show_value=True)
    energy_ui = mo.ui.slider(label="Energy target: ",start=0.1,stop=2.0,step=0.1,value=1.2,show_value=True)
    target_ui = mo.hstack([energy_ui,power_ui,],justify='start')
    target_ui
    return energy_ui, power_ui, target_ui


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Solution 1: Convex relaxation

    This solution relaxes the power target to an inequality to achieve convexity. It allows the power target to be reached but not exceeded, while preserving the energy target using only a load scalar at each node but no power offset.
    """)
    return


@app.cell
def _(cp, cvx_options, np):
    def solution_1(X:np.array,P_target:float,E_target:float,options:dict={}):
        """Solve the single energy/power target using scale only

        Arguments
        ---------
        - `X(T, n)`: nonnegative array of time-series signals
        - `E_target`: scalar energy target
        - `P_target`: scalar power target
        """
        T, n = X.shape

        a = cp.Constant(X.sum(axis=0),'a')          # column energy weights, shape (n,)

        P = cp.Constant(P_target,'P')
        E = cp.Constant(E_target,'E')

        # Decision variable: per-column scaling factors
        s = cp.Variable(n, nonneg=True, name='s')

        # Constraints
        constraints = [
            a @ s == E,     # energy equality (affine)
            X @ s <= P,     # power inequality (convex relaxation)
        ]

        objective = cp.Minimize(cp.sum_squares(s-1))

        prob = cp.Problem(objective, constraints)
        result = prob.solve(**cvx_options(**options))

        if prob.status not in ("infeasible", "unbounded"):
            scale = s.value
            print("scaling factors:", scale.round(4))
            print("achieved energy:", a @ scale, " target:", E.value.round(1))
            print("achieved power :", np.max(X @ scale), " target:", P.value.round(3))
        else:
            print("Problem status:", prob.status)
        return result,prob

    return (solution_1,)


@app.cell
def _(target_ui):
    target_ui
    return


@app.cell
def _(E, P, X, plot_results, solution_1):
    _result,_problem = solution_1(X, P, E)
    plot_results(_problem)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Solution 2: Tight power via offsets (scalarized formulation)

    Solution 2 tightens the power target by allowing power offsets in addition to scales for each node. The trade-off on is controlled by the $\lambda$ hyper-parameter. Power should be at target for $\lambda=$ and scales should approach unity when $\lambda \to \infty$.
    """)
    return


@app.cell
def _(cp, cvx_options, np):
    def solution_2(X:np.array,
                   P_target:float,
                   E_target:float,
                   *,
                   options:dict={"solver":"clarabel"},
                  ):
        """Solve the single energy/power target using scale only

        Arguments
        ---------
        - `X(T, n)`: nonnegative array of time-series signals
        - `E_target`: scalar energy target
        - `P_target`: scalar power target
        """
        T, n = X.shape

        a = cp.Constant(X.sum(axis=0),name='a') # column energy weights, shape (n,)

        E = cp.Constant(E_target,name='E')
        P = cp.Constant(P_target,name='P')

        s = cp.Variable(n, nonneg=True, name='s')
        b = cp.Variable(n, name='b')

        # Constraints
        constraints = [
            a @ s + T * cp.sum(b) == E,         # energy exact (affine)
            cp.max(X @ s) + cp.sum(b) <= P,     # power inequality (convex relaxation)
        ]
        objective = cp.Maximize(cp.sum(b))

        prob = cp.Problem(objective, constraints)
        result = prob.solve(**cvx_options(**options))

        if prob.status not in ("infeasible", "unbounded"):
            scale = s.value.round(4)
            offset = b.value.round(4)
            print("scaling factors:", scale)
            print("power offsets:", offset)
            print("achieved energy:", (a @ s + T*b).value, " target:", E.value)
            print("achieved power :", (cp.max(X@s,axis=0) + b).value, " target:", P.value)
        else:
            print("Problem status:", prob.status)
        return result,prob

    return (solution_2,)


@app.cell
def _(target_ui):
    target_ui
    return


@app.cell
def _(E, P, X, plot_results, solution_2):
    _result,_problem = solution_2(X, P, E)
    plot_results(_problem)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Solution 3: Bi-objective, scalarized

    TODO: explanation
    """)
    return


@app.cell
def _(mo):
    lambda_ui = mo.ui.slider(
        label=r"$\lambda$: ",
        start=0,
        stop=10,
        step=0.1,
        value=0.0,
        debounce=True,
        show_value=True,
    )
    return (lambda_ui,)


@app.cell
def _(lambda_ui, mo, target_ui):
    mo.hstack([target_ui,lambda_ui],justify='start')
    return


@app.cell
def _(cp, cvx_options, np):
    def solution_3(X:np.array,
                   P_target:float,
                   E_target:float,
                   *,
                   lam:float=1.0,
                   options:dict={"solver":"clarabel"},
                  ):
        """Solve the single energy/power target using scale only

        Arguments
        ---------
        - `X(T, n)`: nonnegative array of time-series signals
        - `E_target`: scalar energy target
        - `P_target`: scalar power target
        - `lam`: power target objective hyperparameter
        """
        T, n = X.shape

        a = cp.Constant(X.sum(axis=0),name='a')          # column energy weights, shape (n,)

        E = cp.Constant(E_target,name='E')
        P = cp.Constant(P_target,name='P')

        s = cp.Variable(n, nonneg=True, name='s')
        b = cp.Variable(n, name='b')

        # Constraints
        constraints = [
            a @ s + T * cp.sum(b) == E, # energy exact (affine)
            cp.max(X@s,axis=0) + cp.sum(b) <= P,     # power inequality (convex relaxation)
        ]
        objective = cp.Minimize(cp.sum_squares(s - 1) - cp.Parameter(value=lam,name="lambda") * cp.sum(b))

        prob = cp.Problem(objective, constraints)
        result = prob.solve(**cvx_options(**options))

        if prob.status not in ("infeasible", "unbounded"):
            scale = s.value.round(4)
            offset = b.value.round(4)
            print("scaling factors:", scale)
            print("power offsets:", offset)
            print("achieved energy:", (a @ s + T*b).value, " target:", E.value)
            print("achieved power :", (cp.max(X@s,axis=0) + b).value, " target:", P.value)
        else:
            print("Problem status:", prob.status)
        return result,prob

    return (solution_3,)


@app.cell
def _(E, P, X, plot_results, solution_3):
    _result,_problem = solution_3(X, P, E)
    plot_results(_problem)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Solution 4: Tri-objective, soft-energy

    TODO: explanation
    """)
    return


@app.cell
def _(cp, np):
    def solution_4(X:np.array,
                   P_target:float,
                   E_target:float,
                   *,
                   lam:float=1.0,
                   mu:float=1.0,
                   **options,
                  ):
        """Solve the single energy/power target using scale only

        Arguments
        ---------
        - `X(T, n)`: nonnegative array of time-series signals
        - `E_target`: scalar energy target
        - `P_target`: scalar power target
        - `lam`: power target objective hyperparameter (presses peak to ceiling)
        - `mu`: energy target objective hyperparameter (recovers energy equality)   
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

    return (solution_4,)


@app.cell
def _(mo):
    mu_ui = mo.ui.slider(label=r"$\mu$: ",start=0, stop=10,step=0.01,value=0.0,debounce=True,show_value=True)
    return (mu_ui,)


@app.cell
def _(lambda_ui, mo, mu_ui, target_ui):
    mo.hstack([target_ui,lambda_ui,mu_ui],justify='start')
    return


@app.cell
def _(E, P, X, lambda_ui, mu_ui, plot_results, solution_4):
    _result,_problem = solution_4(X,P,E,lam=lambda_ui.value,mu=mu_ui.value)
    plot_results(_problem)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Multiple Non-overlapping Regions

    In this formulation of the problem the energy target regions are a strict superset of the power target regions.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    TODO: not implemented yet
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Multiple Overlapping Regions

    In this formulation of the problem the energy target regions and power target regions overlap.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    TODO: not implemented yet
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell
def _(E, P, X, data, energy_ui, mo, plt, power_ui):
    def plot_results(_problem):
        if _problem.status not in ("infeasible", "unbounded"):
            _scale = _problem.variables()[0].value
            _offset = _problem.variables()[1].value if len(_problem.variables()) > 1 else None
            _energy = 1 - (X * _scale + (0 if _offset is None else _offset)).sum(axis=None) / E
            _power = 1 - (X * _scale + (0 if _offset is None else _offset)).sum(axis=1).max() / P
            _scale.round(4),_energy.round(1),_power.round(3)
            plt.close()
            plt.figure(figsize=(10,7))
            plt.bar(height=_scale,x=data.columns,label="Scale")
            if not _offset is None:
                plt.bar(height=_offset,x=data.columns,label="Offset")
                plt.legend()
            plt.title(f"Energy target: {energy_ui.value} / Power target: {power_ui.value} \n Solution status: {_problem.status.title().replace('_',' ')} \n Energy error: {_energy*100:.2f}% / Power error: {_power*100:.2f}%")
            plt.xticks(rotation=90)
            plt.grid()
            _result = plot_2 = plt.gca()
        else:
            _result = mo.md(f"**<font color=red>ERROR: {_problem.status}</font>**")
        return _result

    def cvx_options(**kwargs):
        options = {
            "solver":"clarabel",
            "verbose":True,
        }
        options.update(kwargs)
        return options


    return cvx_options, plot_results


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
