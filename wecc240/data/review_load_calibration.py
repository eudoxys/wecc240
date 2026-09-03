import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _(pd):
    # input data
    county_total = pd.read_csv("county_total.csv",index_col=[0],parse_dates=[0])
    county_dg = pd.read_csv("county_dg.csv",index_col=[0],parse_dates=[0])
    energy_target = pd.read_csv("energy_target.csv",index_col=[0],parse_dates=[0])
    peak_target = pd.read_csv("peak_target.csv",index_col=[0],parse_dates=[0])
    states = sorted(set(x.split()[-1] for x in county_total.columns))
    county_groups = pd.DataFrame(data={x:[(1 if y.endswith(x) else 0) for y in county_total.columns] for x in states},
                                 index=county_total.columns)
    state_total = pd.DataFrame(
        data = {
            x: (county_total * county_groups[x]).sum(axis=1)
            for x in county_groups.columns
        }
    )
    _groups = pd.read_csv("state_groups.csv",index_col=[0])
    region_total = pd.DataFrame(
        data={
            x: (county_total * _groups[x]).sum(axis=1)
            for x in _groups.columns
        },
        index=county_total.index,
    )
    return (
        county_dg,
        county_total,
        energy_target,
        peak_target,
        region_total,
        state_total,
        states,
    )


@app.cell
def _(calendar, month_ui, pd, year_ui):
    _year = year_ui.value
    _month = month_ui.value
    _,_lastday = calendar.monthrange(_year,_month)
    dt = pd.date_range(start=f"{_year}-{_month}-01 00:00:00+0000",end=f"{_year}-{_month}-{_lastday} 23:59:59+0000",freq="1h")
    return (dt,)


@app.cell
def _(dt_month, energy_target, plot_options):
    energy_plot = (energy_target.loc[dt_month] / 1e6).plot(kind="bar", figsize=plot_options["figsize"],grid=True,ylabel="Energy (TWh)")
    return (energy_plot,)


@app.cell
def _(dt_month, peak_target, plot_options):
    peak_plot = (peak_target.loc[dt_month]/1e3).plot(kind="bar", figsize=plot_options["figsize"],grid=True,ylabel="Power (GW)")
    return (peak_plot,)


@app.cell
def _(
    county_dg,
    county_total,
    dt,
    energy_plot,
    mo,
    peak_plot,
    plot_options,
    region_total,
    state_total,
    state_ui,
):
    county_names = [
        x for x in county_total.columns if x.endswith(state_ui.value)
    ]
    _countyload = (county_total.loc[dt,county_names] / 1e3).round(3)
    _countydg = (county_dg.loc[dt,county_names] / 1e3).round(3)
    _loadplot = _countyload.sum(axis=1).plot(**plot_options,label="Load")
    _dgplot = _countydg.sum(axis=1).plot(**plot_options,label="DG")
    input_ui = mo.ui.tabs(
        {
            "State load (GW)": mo.ui.tabs(
                {
                    "Data": _countyload,
                    "Plot": _loadplot,
                }
            ),
            "State DG (GW)": mo.ui.tabs(
                {
                    "Data": _countydg,
                    "Plot": _dgplot,
                }
            ),
            "Energy target (TWh)": energy_plot,
            "Peak target (GW)": peak_plot,
            "State groups": (state_total.loc[dt] / 1e3).plot(
                kind="area", **plot_options
            ),
            "Region groups": (region_total.loc[dt] / 1e3).plot(**plot_options),
        }
    )
    return county_names, input_ui


@app.cell
def _(calendar, mo):
    _options = {y:x for x,y in enumerate(calendar.month_name) if y}
    month_ui = mo.ui.dropdown(options=_options,value=calendar.month_name[8])
    year_ui = mo.ui.dropdown(options=range(2018,2023),value=2020)
    yearmonth_ui = mo.hstack([mo.md("Date range:"),month_ui,year_ui],justify='start')
    return month_ui, year_ui, yearmonth_ui


@app.cell
def _(mo, states):
    state_ui = mo.ui.dropdown(label="State:",options=states,value=states[0])
    return (state_ui,)


@app.cell
def _(mo, state_ui, yearmonth_ui):
    mo.hstack([yearmonth_ui,state_ui])
    return


@app.cell
def _(counties_caiso, county_dg, county_total, dt):
    # problem setup
    X = county_total.loc[dt, :].values
    D = county_dg.loc[dt, :].values
    g_wecc = [1.0 for x in county_total.columns]
    g_caiso = [
        1.0 if x in counties_caiso else 0.0 for x in county_total.columns
    ]
    dt_month = dt[0].to_pydatetime()
    state_ndx = {
        y: n
        for n, y in enumerate(
            sorted(set(x.split()[-1] for x in county_total.columns))
        )
    }
    state_groups = {
        m: [1 if c.split()[-1] == n else 0 for c in county_total.columns]
        for n, m in state_ndx.items()
    }
    return D, X, dt_month, g_caiso, g_wecc, state_groups, state_ndx


@app.cell
def _(
    D,
    X,
    calibrate,
    dt_month,
    energy_target,
    g_caiso,
    g_wecc,
    get_gamma,
    get_lam,
    get_mu,
    mo,
    np,
    peak_target,
    state_groups,
    state_ndx,
):
    E_state = {
        state_ndx[x]: y
        for x, y in energy_target.loc[dt_month].to_dict().items()
    }
    P_caiso, P_wecc = peak_target.loc[dt_month].values
    with mo.capture_stdout() as _buf:
        with mo.status.spinner("Solving problem"):
            result = calibrate(
                X,
                D,
                state_groups,
                np.array(g_caiso),
                np.array(g_wecc),
                E_state,
                P_caiso,
                P_wecc,
                gamma=get_gamma(),
                mu=np.array(get_mu()),
                lam=np.array(get_lam()),
                eps=1e-6,
            )
    stdout = _buf.getvalue()
    return E_state, P_caiso, P_wecc, result, stdout


@app.cell
def _(mo, state_groups):
    get_gamma,set_gamma = mo.state(1.0)
    get_mu,set_my = mo.state([1.0]*len(state_groups))
    get_lam,set_lam = mo.state([1.0]*2)
    return get_gamma, get_lam, get_mu, set_gamma, set_lam


@app.cell
def _(
    get_gamma,
    get_lam,
    get_mu,
    mo,
    set_gamma,
    set_lam,
    set_mu,
    state_ndx,
    state_ui,
):
    _range = [0] + sorted([x * y for x in [1, 2, 5] for y in [10**n for n in range(-6, 6)]])

    def _update_mu(x):
        mu = get_mu()
        mu[state_ndx[state_ui.value]] = x
        set_mu(mu)

    def _update_lam_caiso(x):
        lam = get_lam()
        lam[0] = x
        set_lam(lam)

    def _update_lam_wecc(x):
        lam = get_lam()
        lam[1] = x
        set_lam(lam)

    gamma_ui = mo.ui.slider(
            label=r"$\gamma$",
            steps=_range,
            value=get_gamma(),
            show_value=True,
            debounce=True,
            on_change=set_gamma,
        )
    mu_ui = mo.ui.slider(
            label=rf"$\mu_{{{state_ui.value}}}$",
            steps=_range,
            value=get_mu()[state_ndx[state_ui.value]],
            show_value=True,
            debounce=True,
            on_change=_update_mu,
        )
    lam_caiso_ui = mo.ui.slider(
            label=r"$\lambda_{CAISO}$",
            steps=_range,
            value=get_lam()[0],
            show_value=True,
            debounce=True,
            on_change=_update_lam_caiso
        )
    lam_wecc_ui = mo.ui.slider(
            label=r"$\lambda_{WECC}$",
            steps=_range,
            value=get_lam()[1],
            show_value=True,
            debounce=True,
            on_change=_update_lam_wecc
        )
    return gamma_ui, lam_caiso_ui, lam_wecc_ui, mu_ui


@app.cell
def _(
    D,
    E_state,
    P_caiso,
    P_wecc,
    X,
    county_ids,
    county_names,
    g_caiso,
    g_wecc,
    gamma_ui,
    lam_caiso_ui,
    lam_wecc_ui,
    mo,
    mu_ui,
    pd,
    state_groups,
    stdout,
):
    _tabs = mo.ui.tabs({
        "X": pd.DataFrame(X[:,county_ids],columns=county_names).round(2),
        "D": pd.DataFrame(D[:,county_ids],columns=county_names).round(2),
        "state_groups": mo.ui.table(state_groups,selection=None),
        "g_caiso": mo.ui.table(g_caiso,selection=None),
        "g_wecc": mo.ui.table(g_wecc,selection=None),
        "E_state": mo.ui.table(E_state,selection=None),
        "P_caiso": P_caiso,
        "P_wecc": P_wecc,
        "Diagnostics": mo.md(f"```\n{stdout}\n```")
    })
    params_ui = mo.hstack([gamma_ui,mu_ui,lam_caiso_ui,lam_wecc_ui])
    problem_ui = mo.vstack([params_ui,_tabs])
    return params_ui, problem_ui


@app.cell
def _(L, county_total, dt, pd):
    output = pd.DataFrame(L,columns=county_total.columns,index=county_total.loc[dt].index)
    output_ui = output.round(2)
    return (output_ui,)


@app.cell
def _(
    D,
    E_state,
    P_caiso,
    P_wecc,
    X,
    evaluate,
    g_caiso,
    g_wecc,
    np,
    result,
    state_groups,
):
    L, energy_dev, power_dev, shape_dev = evaluate(
        result["scale"],
        result["offset"],
        X,
        D,
        state_groups,
        np.array(g_caiso),
        np.array(g_wecc),
        E_state,
        P_caiso,
        P_wecc,
    )
    return L, energy_dev, power_dev, shape_dev


@app.cell
def _(
    L,
    X,
    county_names,
    evaluation_ui,
    mo,
    pd,
    plot_options,
    result,
    state_groups,
    state_ndx,
    state_ui,
):
    county_ids = [
        n
        for n, x in enumerate(state_groups[state_ndx[state_ui.value]])
        if x == 1
    ]
    _plot = (pd.DataFrame(L[:, county_ids]).sum(axis=1) / 1e3).plot(
        **plot_options
    )
    (pd.DataFrame(X[:, county_ids]).sum(axis=1) / 1e3).plot(
        **plot_options, ax=_plot
    )
    _plot.legend(["New", "Old"])
    solution_ui = mo.ui.tabs(
        {
            "Evaluation": evaluation_ui,
            "Load": mo.mpl.interactive(_plot),
            "Scale": pd.DataFrame(
                data=[result["scale"][county_ids]], columns=county_names
            ).T.plot(kind="bar", ylabel="Power scale [pu]", legend=None, figsize=plot_options["figsize"]),
            "Offset": pd.DataFrame(
                data=[result["offset"][county_ids]], columns=county_names
            ).T.plot(kind="bar", ylabel="Power offset [MW]", legend=None, figsize=plot_options["figsize"]),
        }
    )
    return county_ids, solution_ui


@app.cell
def _(
    E_state,
    P_caiso,
    P_wecc,
    energy_dev,
    mo,
    month_ui,
    np,
    pd,
    plot_options,
    power_dev,
    shape_dev,
    states,
    year_ui,
):
    evaluation_ui = mo.ui.tabs(
        {
            "Energy": pd.DataFrame(
                data=[energy_dev / np.array(list(E_state.values())) * 100],
                columns=states,
            ).T.plot(
                kind="bar",
                ylabel="Energy deviation (%)",
                grid=True,
                figsize=plot_options["figsize"],
                legend=None,
            ),
            "Power": pd.DataFrame(
                data=[power_dev / np.array([P_caiso,P_wecc]) * 100],
                columns=["CAISO","WECC"],
            ).T.plot(
                kind="bar",
                ylabel="Power deviation (%)",
                grid=True,
                figsize=plot_options["figsize"],
                legend=None,
            ),
            "Shape": pd.DataFrame(data=[shape_dev/1e3],index=[f"{month_ui.selected_key} {year_ui.value}"],columns=["WECC"]).plot(kind="bar",ylabel="Shape Change (GW)",figsize=plot_options["figsize"],grid=True,legend=None),
        }
    )
    return (evaluation_ui,)


@app.cell
def _(
    input_ui,
    mo,
    output_ui,
    parameters_ui,
    params_ui,
    problem_ui,
    solution_ui,
):
    mo.ui.tabs({
        "Inputs":input_ui,
        "Problem": problem_ui,
        "Solution": mo.vstack([params_ui,solution_ui]),
        "Parameters": parameters_ui,
        "Output": output_ui,
    })
    return


@app.cell
def _(get_gamma, get_lam, get_mu, mo):
    # gamma=get_gamma(),
    # mu=np.array(get_mu()),
    # lam=np.array(get_lam()),
    # eps=1e-6,

    parameters_ui = mo.md(f"""
    $\gamma = {get_gamma()}$

    $\mu = {get_mu()}$

    $\lambda = {get_lam()}$

    $\epsilon = 10^{{-6}}$
    """)
    return (parameters_ui,)


@app.cell
def _(Counties, county_total):
    county_ndx = {x:n for n,x in enumerate(county_total.columns)} # index into load data columns
    counties = Counties(use_index="SYSTEM",selection="WECC",set_index="REGION")
    counties["COUNTY_ST"] = [f"{x} {y}" for x,y in counties[["COUNTY","ST"]].values]
    counties["COUNTY_NDX"] = [county_ndx[x] if x in county_ndx else -1 for x in counties["COUNTY_ST"].values]
    counties.drop(counties[counties["COUNTY_NDX"]==-1].index,inplace=True,axis=0)
    counties_caiso = set(counties.loc["CAISO","COUNTY_ST"].values)
    return (counties_caiso,)


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import calendar
    from fips.counties import Counties
    from load_calibrate import calibrate, evaluate
    import numpy as np
    plot_options = {
        "figsize": (10,7),
        "grid": True,
        "xlabel": "Date/Time (UTC)",
        "ylabel": "Power (GW)"
    }
    return Counties, calendar, calibrate, evaluate, mo, np, pd, plot_options


if __name__ == "__main__":
    app.run()
