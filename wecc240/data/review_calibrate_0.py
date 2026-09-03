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
def _(mo):
    mo.array
    return


@app.cell
def _(mo, region_ui):
    # Show normalization UI
    mo.hstack(
        [
            region_ui,
            mo.accordion(
                {
                    "ℹ️ ": "Select the balancing authority (BA) to collect and display results. Selecting a plotting region does not effect the solution.\n\n<b>Note</b>: the power target is for WECC unless CAISO alone is chosen."
                }
            ),
        ]
    )
    return


@app.cell
def _(county_total, mo, plot_ui, result_ui):
    # Show main UI
    mo.accordion(
        {
            "Data": county_total.round(3),
            "Solution":plot_ui,
            "Results":result_ui,
        },multiple=True
    )
    return


@app.cell
def _(clear_results, counties, mo):
    # UI elements
    region_ui = mo.ui.multiselect(options=counties.index.unique(),label="Region:")
    month_ui = mo.ui.dropdown(
        options={
            "January": 1,
            "February": 2,
            "March": 3,
            "April": 4,
            "May": 5,
            "June": 6,
            "July": 7,
            "August": 8,
            "September": 9,
            "October": 10,
            "November": 11,
            "December": 12,
        },
        value="August",
    )
    year_ui = mo.ui.dropdown(options=range(2018, 2023), value=2020)
    gamma_options = [0] + sorted(
        [x * y for x in [1, 2, 5] for y in [10**n for n in range(-6, 6)]]
    )
    gamma_ui = mo.ui.slider(
        label=r"$\gamma$",
        steps=gamma_options,
        value=0.0,
        show_value=True,
        debounce=True,
    )
    mu_options = [0] + sorted(
        [x * y for x in [1, 2, 5] for y in [10**n for n in range(-6, 6)]]
    )
    mu_ui = mo.ui.slider(
        label=r"$\mu$: ",
        steps=mu_options,
        value=0.0,
        show_value=True,
        debounce=True,
    )
    lambda_options = [0] + sorted(
        [x * y for x in [1, 2, 5] for y in [10**n for n in range(-6, 6)]]
    )
    lambda_ui = mo.ui.slider(
        label=r"$\lambda$: ",
        steps=lambda_options,
        value=0.0,
        show_value=True,
        debounce=True,
    )
    epsilon_options = [10**n for n in range(-6, 0)]
    epsilon_ui = mo.ui.slider(
        label=r"$\epsilon$",
        steps=epsilon_options,
        value=1e-6,
        show_value=True,
        debounce=True,
    )
    target_ui = mo.hstack(
        [
            mo.vstack(
                [
                    mo.hstack([gamma_ui, mu_ui, lambda_ui, epsilon_ui], justify="start"),
                ],
            ),
            mo.accordion(
                {
                    "ℹ️": r"The $\gamma$ parameter is the primary regularizer and prevents crushing of the output. The $\mu$ parameter controls the recovery of the energy target. The $\lambda$ parameter drives the peak power to the power target. The $\epsilon$ parameter is the symmetric well-posedness ridge."
                }
            ),
        ],
        justify="start",
    )
    clear_ui = mo.ui.button(label="Clear results", on_click=clear_results)
    return (
        clear_ui,
        epsilon_options,
        epsilon_ui,
        gamma_options,
        gamma_ui,
        lambda_options,
        lambda_ui,
        month_ui,
        mu_options,
        mu_ui,
        region_ui,
        target_ui,
        year_ui,
    )


@app.cell
def _(mo, selected_counties):
    _sel = selected_counties
    _len = len(_sel)
    county_groups = {f"{_sel[n]} — {_sel[min(_len,n+50)-1]}":_sel[n:min(_len,n+50)-1] for n in range(0,len(_sel),50)}
    county_ui = mo.ui.tabs({x:mo.md("") for x in county_groups}) if _len > 50 else mo.md("")
    return county_groups, county_ui


@app.cell
def _(
    clear_ui,
    get_history,
    mo,
    mu_options,
    pd,
    plot_results,
    problem,
    sweep_epsilon_ui,
    sweep_gamma_ui,
    sweep_lambda_ui,
    sweep_mu_ui,
    target_ui,
):
    # Display history of results
    plot_ui = mo.vstack([target_ui,plot_results(problem)],)
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
                "Total (%)",
            ],
        )
        .reset_index(drop=True)
        .set_index(["BA","Y/M","E","P","γ","μ","λ","ε"])
    )
    result_ui = mo.vstack(
        [
            mo.ui.table(
                _results.round(6).sort_index(),#sort_values(["BA","Y/M","Perr (%)","Score","Eerr (%)"]),
                selection=None,page_size=len(mu_options)
            ),
            mo.hstack([sweep_gamma_ui,sweep_mu_ui,sweep_lambda_ui,sweep_epsilon_ui,clear_ui,],justify='start'), 
        ]
    )
    return plot_ui, result_ui


@app.cell
def _(E_state):
    E_state
    return


@app.cell
def _():
    #
    # Single-shot solution update
    #
    return


@app.cell
def _(
    D,
    E_state,
    P_caiso_raw,
    P_wecc_raw,
    X,
    calibrate,
    cvx_options,
    epsilon_ui,
    g_caiso,
    g_wecc,
    gamma_ui,
    lambda_ui,
    mo,
    mu_ui,
    np,
    options,
    state_groups,
    state_ndx,
):
    # Obtain the solution to the problem
    with mo.status.spinner("Solving problem..."):
        params = {
            "gamma": gamma_ui.value,
            "mu": np.array([mu_ui.value]*len(state_ndx)),
            "lam": np.array([lambda_ui.value]*2),
            "eps": epsilon_ui.value,
        }    
        cost, problem = calibrate(
            X,D,
            state_groups, 
            np.array(g_caiso), np.array(g_wecc), 
            E_state,
            P_caiso_raw, P_wecc_raw,
            options=cvx_options(**options),
            **params,
            )
    return (problem,)


@app.cell
def _():
    #
    # Support Functions
    #
    return


@app.cell
def _(E_state, P_caiso_raw, P_wecc_raw, region_ui):
    E_target = sum(E_state.values())/1e6
    P_target = ( P_wecc_raw if region_ui.value != ["CAISO"] else P_caiso_raw ) /1e3 # GW
    return E_target, P_target


@app.cell
def _(
    E_target,
    P_target,
    X,
    county_groups,
    county_ndx,
    county_total,
    county_ui,
    get_results,
    mo,
    pd,
    plt,
    region_ndx,
    units,
):
    # Generate plot of results
    def plot_results(problem):
        """Generate plot of results"""
        if problem.status not in ("infeasible", "unbounded"):

            try:
                _counties = [county_ndx[x] for x in county_groups[county_ui.value]]
            except AttributeError:
                _counties = region_ndx
        
            Y, energy_ferr, power_ferr, rms_change = get_results(problem)
            peak = X[:,_counties].sum(axis=1).max()

            plt.close()

            pd.DataFrame(
                data={
                    "Original": X[:,_counties].max(axis=0)/1e3, # convert to GW
                    "Rescaled": Y[:,_counties].max(axis=0)/1e3, # convert to GW
                },
                index=county_total.columns[_counties],
            ).plot(
                kind="bar",
                grid=True,
                figsize=(11, 7),
                ylabel=f"Max power ({units})",
            )
            plt.title(
                f"""Energy target: {E_target:.1f} TWh / Power target: {P_target:.3f} GW
    Solution status: {problem.status.title().replace('_', ' ')}
    Energy error: {energy_ferr * 100:.2f}% / Power error: {power_ferr * 100:.2f}% / RMS change: {rms_change*100:.2f}%"""
            )
            plt.legend()
            plt.xticks(rotation=90)
            _result = plot_2 = plt.gca()
        else:
            _result = mo.md(
                f"**<font color=red>ERROR: {problem.status}</font>**"
            )
        return mo.vstack([county_ui,_result])

    return (plot_results,)


@app.cell
def _(
    D,
    E_state,
    E_target,
    P_caiso_raw,
    P_target,
    P_wecc_raw,
    X,
    evaluate,
    g_caiso,
    g_wecc,
    get_scalar,
    get_variable,
    get_vector,
    month_ui,
    record_result,
    region_ui,
    state_groups,
    year_ui,
):
    def get_results(problem):
        """Calculate and record results of problem solve"""
        Y, energy_ferr, power_ferr, rms_change = evaluate(
            get_variable(problem,"s"), get_variable(problem,"b"),
            X, D,
            state_groups, 
            g_caiso, g_wecc,
            E_state, 
            P_caiso_raw, P_wecc_raw,
        )

        record_result(
            ", ".join(region_ui.value) if region_ui.value else "WECC",
            f"{year_ui.value:04d}-{month_ui.value:02d}",
            round(E_target, 1),
            round(P_target, 1),
            round(get_scalar(problem, "gamma"), 6),
            round(get_vector(problem, "mu").mean(), 6),
            round(get_vector(problem, "lam").mean(), 6),
            round(get_scalar(problem, "eps"), 6),
            round(abs(energy_ferr * 100), 2),
            round(abs(power_ferr * 100), 2),
            round(rms_change * 100, 3),
        )
        return Y, energy_ferr, power_ferr, rms_change

    return (get_results,)


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
def _(
    E,
    P,
    X,
    epsilon_ui,
    gamma_options,
    get_results,
    lambda_ui,
    mo,
    mu_ui,
    solution,
):
    # Sweep values of gamma and record solution results
    def sweep_gamma(*args, **kwargs):
        with mo.status.progress_bar(
            title="Sweeping values of gamma",
            total=len(gamma_options),
            remove_on_exit=True,
        ) as _bar:
            for gamma in gamma_options:
                _bar.update(subtitle=f"Solving {gamma=}")
                get_results(
                    solution(
                        X,
                        E,
                        P,
                        gamma=gamma,
                        mu=mu_ui.value,
                        lam=lambda_ui.value,
                        eps=epsilon_ui.value,
                    )[1]
                )

    sweep_gamma_ui = mo.ui.button(label=r"Sweep $\gamma$", on_click=sweep_gamma)
    return (sweep_gamma_ui,)


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
    solution,
):
    # Sweep values of mu and record solution results
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

    sweep_mu_ui = mo.ui.button(label=r"Sweep $\mu$", on_click=sweep_mu)
    return (sweep_mu_ui,)


@app.cell
def _(
    E,
    P,
    X,
    epsilon_ui,
    gamma_ui,
    get_results,
    lambda_options,
    mo,
    mu_ui,
    solution,
):
    # sweep values of lambda and record results
    def sweep_lambda(*args, **kwargs):
        with mo.status.progress_bar(
            title="Sweeping values of lambda",
            total=len(lambda_options),
            remove_on_exit=True,
        ) as _bar:
            for lam in lambda_options:
                _bar.update(subtitle=f"Solving {lam=}")
                get_results(
                    solution(
                        X,
                        E,
                        P,
                        gamma=gamma_ui.value,
                        mu=mu_ui.value,
                        lam=lam,
                        eps=epsilon_ui.value,
                    )[1]
                )

    sweep_lambda_ui = mo.ui.button(label=r"Sweep $\lambda$", on_click=sweep_lambda)
    return (sweep_lambda_ui,)


@app.cell
def _(
    E,
    P,
    X,
    epsilon_options,
    gamma_ui,
    get_results,
    lambda_ui,
    mo,
    mu_ui,
    solution,
):
    # Sweep values of epsilon and record solution results
    def sweep_epsilon(*args, **kwargs):
        with mo.status.progress_bar(
            title="Sweeping values of epsilon",
            total=len(epsilon_options),
            remove_on_exit=True,
        ) as _bar:
            for eps in epsilon_options:
                _bar.update(subtitle=f"Solving {eps=}")
                get_results(
                    solution(
                        X,
                        E,
                        P,
                        gamma=gamma_ui.value,
                        mu=mu_ui.value,
                        lam=lambda_ui.value,
                        eps=eps
                    )[1]
                )

    sweep_epsilon_ui = mo.ui.button(label=r"Sweep $\epsilon$", on_click=sweep_epsilon)
    return (sweep_epsilon_ui,)


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
    return


@app.cell
def _(mo, pd):
    # GIS data
    with mo.status.spinner("Reading bus GIS data"):
        bus_gis = pd.read_csv("https://raw.githubusercontent.com/eudoxys/wecc240/refs/heads/main/wecc240/data/bus_gis.csv")
        load_bus = bus_gis[bus_gis["LOAD"] > 0]
    return


@app.cell
def _(cal, month_ui, pd, year_ui):
    # Date range
    _year = year_ui.value
    _month = month_ui.value
    date_range = pd.date_range(
        start=f"{_year}-{_month:02d}-01 00:00:00+0000",
        end=f"{_year}-{_month:02d}-{cal.monthrange(_year,_month)[1]} 23:00:00+0000",
        freq="1h")
    return


@app.cell
def _(pd):
    # read county-level total loads
    county_total = pd.read_csv("county_total.csv", index_col=[0], parse_dates=[0])
    county_dg = pd.read_csv("county_dg.csv", index_col=[0], parse_dates=[0])
    assert set(county_total.columns) == set(county_dg.columns), "total and DG counties do not match"
    county_ndx = {x:n for n,x in enumerate(county_total.columns)} # index into load data columns
    return county_dg, county_ndx, county_total


@app.cell
def _(Counties, county_ndx):
    # read county GIS data
    counties = Counties(use_index="SYSTEM",selection="WECC",set_index="REGION")
    counties["COUNTY_ST"] = [f"{x} {y}" for x,y in counties[["COUNTY","ST"]].values]
    counties["COUNTY_NDX"] = [county_ndx[x] if x in county_ndx else -1 for x in counties["COUNTY_ST"].values]
    counties.drop(counties[counties["COUNTY_NDX"]==-1].index,inplace=True,axis=0)
    return (counties,)


@app.cell
def _(pd):
    # read state energy targets
    state_mwh = pd.read_csv("state_mwh.csv",index_col=[0,1],parse_dates=[0])
    return (state_mwh,)


@app.cell
def _(pd):
    # read county energy contribution factors
    state_cf = pd.read_csv("state_cf.csv",index_col=[0],parse_dates=[0])
    return (state_cf,)


@app.cell
def _(county_total, pd, state_cf, state_mwh):
    # calculate county_mwh from state_mwh and state_cf
    county_mwh = state_cf.stack().reset_index()
    county_mwh.columns=["timestamp","county","cf"]
    county_mwh["state"] = [x.split()[-1] for x in county_mwh.county]
    county_mwh = pd.merge(county_mwh,state_mwh["load"],left_on=["timestamp","state"],right_index=True)
    county_mwh["energy"] = county_mwh["load"] * county_mwh["cf"]
    county_mwh = county_mwh.drop(["cf","state","load"],axis=1).set_index(["timestamp","county"]).unstack()
    county_mwh.columns = [x[-1] for x in county_mwh.columns]
    county_mwh = county_mwh[county_total.columns]
    return


@app.cell
def _(county_dg, county_total, dt):
    county_total.loc[dt].to_csv("X.csv",index=True,header=True)
    county_dg.loc[dt].to_csv("D.csv",index=True,header=True)
    return


@app.cell
def _(pd):
    # read regional peak loads
    peak_load = pd.read_csv("peak_load.csv",index_col=[1,0],parse_dates=[0])
    return (peak_load,)


@app.cell
def _(cvx_options):
    # warnings.simplefilter('error')
    options = cvx_options(verbose=True,solver="clarabel")
    units = "GW"
    return options, units


@app.cell
def _(pd):
    dt = pd.date_range(
        start=f"2020-08-01 00:00:00+0000",
        end=f"2020-08-31 23:59:59+0000",
        freq="1h"
        )
    return (dt,)


@app.cell
def _(county_ndx, selected_counties):
    region_ndx = [county_ndx[x] for x in selected_counties]
    return (region_ndx,)


@app.cell
def _(county_total):
    # handle states
    county_names = county_total.columns
    state_ndx = {y:n for n,y in enumerate(set(x.split()[-1] for x in county_total.columns))}
    state_groups = {
        x:[1 if y.split()[-1]==x else 0 for y in county_names] 
        for x in state_ndx.values()
        }
    return state_groups, state_ndx


@app.cell
def _(counties, county_total, region_ui):
    # handle region selection
    selected_counties = [x for x in county_total.columns if not region_ui.value or counties.reset_index().set_index("COUNTY_ST").loc[x,"REGION"] in region_ui.value]
    return (selected_counties,)


@app.cell
def _(counties, county_dg, county_total, dt, peak_load, state_mwh, state_ndx):
    # prepare problem data
    X = county_total.loc[dt,:].values
    D = county_dg.loc[dt,:].values
    g_wecc = [1.0 for x in county_total.columns]
    counties_caiso = set(counties.loc["CAISO","COUNTY_ST"].values)
    caiso_ndx = [n for n,x in enumerate(county_total.columns) if x in counties_caiso]
    wecc_ndx = range(len(county_total.columns))
    g_caiso = [1.0 if x in counties_caiso else 0.0 for x in county_total.columns]
    dt_month = dt[0].to_pydatetime()
    assert (dt_month.day==1 and dt_month.hour==0), "data must begin with first hour of month"
    E_state = {state_ndx[x]:y for x,y in state_mwh.loc[dt_month,"load"].to_dict().items()}
    P_wecc_raw = peak_load.loc["WECC"].resample("MS").ffill().loc[dt_month,"peak_mw"]
    P_caiso_raw = peak_load.loc["CAISO"].resample("MS").ffill().loc[dt_month,"peak_mw"]
    return D, E_state, P_caiso_raw, P_wecc_raw, X, g_caiso, g_wecc


@app.cell
def _():
    # import
    import marimo as mo
    import calendar as cal
    import numpy as np
    import pandas as pd
    import cvxpy as cp
    import matplotlib.pyplot as plt
    from fips import Counties
    from load_calibrate import cvx_options, calibrate, calculate_results, get_scalar, get_parameter, get_vector, get_variable

    return (
        Counties,
        cal,
        calibrate,
        cvx_options,
        get_scalar,
        get_variable,
        get_vector,
        mo,
        np,
        pd,
        plt,
    )


if __name__ == "__main__":
    app.run()
