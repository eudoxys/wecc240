import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook loads the raw 2018 load data and generates the load estimates for other years.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### State/County Selection
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Load data is obtained by state and county.
    """)
    return


@app.cell
def _(county_ui, mo, show_ui, state_ui):
    mo.hstack([mo.hstack([state_ui,county_ui],justify='start'),show_ui])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Raw Load Data
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The raw load data collected from the Eudoxys [loads](https://www.eudoxys.com/loads/loads.html) module using respective sector submodules for the [**Residential**](https://www.eudoxys.com/loads/loads/residential.html), [**Commercial**](https://www.eudoxys.com/loads/loads/commercial.html), [**Industrial**](https://www.eudoxys.com/loads/loads/industry.html) and [**Agricultural**](https://www.eudoxys.com/loads/loads/agriculture.html) tabs. The **Sector** tab shows the county-level annual energy by sector, and the **Enduse** tab shows the county-level annual energy by load enduse aggregation, i.e., baseload, cooling load, and heating load.
    """)
    return


@app.cell
def _(agr, com, enduse_mwh, ind, mo, res, sector_mw, sector_mwh, tot):
    mo.ui.tabs(
        {
            "Energy": mo.hstack([sector_mwh(
                {
                    "Residential": res,
                    "Commercial": com,
                    "Industrial": ind,
                    "Agricultural": agr,
                }),enduse_mwh(
                {
                    "Residential": res,
                    "Commercial": com,
                    "Industrial": ind,
                    "Agricultural": agr,
                })]),
            "Residential": sector_mw(res),
            "Commercial": sector_mw(com),
            "Industrial": sector_mw(ind),
            "Agricultural": sector_mw(agr),
            "Total": sector_mw(tot),
        },
        lazy=True,
    )
    return


@app.cell
def _(pd):
    # load region, state, and county information
    _groups = pd.read_csv("data/state_groups.csv",index_col=[0])
    counties = list(_groups.index)
    states = sorted(set(map(lambda x:x.split()[-1],_groups.index)))
    # wecc_counties = list(_groups[_groups.WECC==1].index)
    # caiso_counties = list(_groups[_groups.CAISO==1].index)
    # noncaiso_counties = list(_groups[_groups.CAISO==0].index)
    state_counties = {x:[" ".join(y.split()[:-1]) for y in counties if y.endswith(x)] for x in states}
    return state_counties, states


@app.cell
def _(mo, states):
    # define state user input
    state_ui = mo.ui.dropdown(label="State:",options=states,value=states[0])
    return (state_ui,)


@app.cell
def _(mo, state_counties, state_ui):
    # define county user input
    _counties = state_counties[state_ui.value]
    county_ui = mo.ui.dropdown(label="County:",options=_counties,value=_counties[0])
    return (county_ui,)


@app.cell
def _(mo):
    # define year user input
    year_ui = mo.ui.dropdown(options=range(2018,2023),value=2018)
    return (year_ui,)


@app.cell
def _(mo):
    # define how user want data shown
    show_ui = mo.ui.radio(label="Show as",options=["Heatmap","Timeseries","Table"],inline=True,value="Heatmap")
    return (show_ui,)


@app.cell
def _(mo, res):
    # define the end-use selector for energy plot
    enduse_ui = mo.ui.dropdown(label="End-use:",options=list(map(lambda x:x.replace("_MW",""), res.columns)),value="elec_total")
    return (enduse_ui,)


@app.cell
def _(agr, com, ind, mo, res, tot):
    # define sector selector user input
    sector_ui = mo.ui.dropdown(
        label="Sector:",
        options={
            "Residential":res,
            "Commercial":com,
            "Industrial":ind,
            "Agricultural":agr,
            "Total":tot,
        },
        value="Total",
    )
    return (sector_ui,)


@app.cell
def _(county_ui, state_ui, year_ui):
    # gather useful user inputs
    state = state_ui.value
    county = county_ui.value
    county_st = f"{county} {state}"
    year = year_ui.value
    return county, county_st, state


@app.cell
def _(enduse_ui):
    enduse_mw = enduse_ui.value + "_MW"
    enduse_gwh = enduse_ui.value + "_GWh"
    return enduse_gwh, enduse_mw


@app.cell
def _(Agriculture, Commercial, Industry, Residential, county, mo, pd, state):
    # load raw data
    with mo.status.progress_bar("Loading data",total=5,remove_on_exit=True) as _bar:
        _bar.update(subtitle="Processing residential")
        res = Residential(state=state,county=county)
        _bar.update(subtitle="Processing commercial")
        com = Commercial(state=state,county=county)
        _bar.update(subtitle="Processing industrial")
        ind = pd.DataFrame(
            data=[Industry(state=state,county=county).T.reset_index(drop=True).to_dict('records')[0]]*len(com.index),
            index=com.index,
        )
        _bar.update(subtitle="Processing agricultural")
        agr = pd.DataFrame(
            data=[Agriculture(state=state,county=county).T.reset_index(drop=True).to_dict('records')[0]]*len(com.index),
            index=com.index,
        )
        _bar.update(subtitle="Processing total")
        tot = res + com + ind + agr
    return agr, com, ind, res, tot


@app.cell
def _(county_st, enduse_mw, enduse_ui, heatmap, mo, pd, show_ui):
    # generate sector power data
    def sector_mw(data: pd.DataFrame):
        """Return data and plot of sector"""
        match show_ui.value:
            case "Table":
                return data.round(3)
            case "Timeseries":
                return data.plot(
                        kind="area",
                        figsize=(10, 6),
                        grid=True,
                        ylabel="Power (MW)",
                        title=county_st,
                    )
            case "Heatmap":
                return mo.vstack([enduse_ui,heatmap(data,enduse_mw)])

    return (sector_mw,)


@app.cell
def _(county_st, enduse_gwh, enduse_ui, mo, pd, plt, show_ui):
    # generate sector energy data
    def sector_mwh(data: dict[str, pd.DataFrame]):
        energy = []
        for name, item in data.items():
            energy.append(item.sum(axis=0).to_frame(name))
        energy = pd.concat(energy, axis=1).T / 1e3
        energy.index.name = "sector"
        energy.columns = [x.replace("_MW", "_GWh") for x in energy.columns]
        plt.cla()
        match show_ui.value:
            case "Table":
                return energy.round(3)
            case _:
                try:
                    plot = energy[f"{enduse_gwh}"].plot(
                            figsize=(6,6),
                            kind="pie",
                            title=county_st,
                            autopct="%.1f%%",
                        )
                except Exception as err:
                    plot = mo.md(f"<font color=red>Plot error: {err}</font>")
                return mo.vstack([enduse_ui,plot])

    return (sector_mwh,)


@app.cell
def _(county_st, mo, pd, plt, sector_ui, show_ui):
    # generate enduse energy data
    def enduse_mwh(data: dict[str, pd.DataFrame]):
        plt.cla()
        enduse = (
            sector_ui.value[
                [
                    "elec_baseload_MW",
                    "elec_cooling_MW",
                    "elec_heating_MW",
                ]
            ]
            .sum(axis=0)
            .to_frame(county_st)
            .T
        )
        enduse.columns = [x.replace("_MW", "_GWh") for x in enduse.columns]
        return (
            enduse
            if show_ui.value == "Table"
            else mo.vstack(
                [
                    sector_ui,
                    enduse.loc[county_st].plot(
                        figsize=(6,6),
                        kind="pie",
                        title=county_st,
                        autopct="%.1f%%",
                    ),
                ]
            )
        )

    return (enduse_mwh,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Weather Data
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The [TSGAM Estimator](https://github.com/nimish/estimator) uses local weather temperature and humidity as the primary independent variables.
    """)
    return


@app.cell
def _(Weather, county, state):
    # load weather data
    weather = Weather(state,county,2018)
    return (weather,)


@app.cell
def _(holdout_ui, mo, year_ui):
    mo.md(fr"""
    The estimator projects the load for the target year {year_ui}. If the year 2018 is selected, a holdout test for {holdout_ui} is used.
    """)
    return


@app.cell
def _(mo, pd):
    _options = {pd.DatetimeIndex([f"2018-{x}-01 00:00:00+0000"])[0].strftime("%B %Y"):x for x in range(1,13)}
    _options["5 days each month"] = 0.15
    holdout_ui = mo.ui.dropdown(
        options=_options,
        value="5 days each month",
    )
    return (holdout_ui,)


@app.cell
def _(holdout_ui, pd, weather):
    # get training and holdout selections
    def get_holdout(data,selection:float=0.15):
    
        if isinstance(selection,int): 
            # entire month selected
            return data.loc[data.index[data.index.month==selection]]
    
        # monthly holdout selected
        nmonths = data.index[-1].month - data.index[0].month
        ndays = int(len(data) * selection / nmonths / 24) + 1
        ndx = data.index[data.index.days_in_month - data.index.day < ndays]
        return data.loc[ndx]

    holdout = get_holdout(weather,holdout_ui.value).index
    training = pd.DatetimeIndex(sorted(set(weather.index) - set(holdout)))
    return holdout, training


@app.cell
def _(county_st, np, plt):
    def heatmap(data,field):
        _data = data[field].array
        _data = np.reshape(_data,(-1,24)).T
        plt.clf()
        plt.figure(figsize=(10,6))
        _ax = plt.imshow(_data,cmap="viridis",aspect="auto")
        _zlabel = field.split("_")
        plt.colorbar(_ax,label=f"{' '.join(_zlabel[:-1]).title()} ({_zlabel[-1]})")
        plt.xlabel("Day of year")
        plt.ylabel("Hour of day (UTC)")
        plt.title(county_st)
        return plt.gca()

    return (heatmap,)


@app.cell
def _(heatmap, weather):
    temperature_heatmap = heatmap(weather,"temperature_degF")
    return (temperature_heatmap,)


@app.cell
def _(heatmap, weather):
    humidity_heatmap = heatmap(weather,"humidity_pc")
    return (humidity_heatmap,)


@app.cell
def _(county_st, humidity_heatmap, mo, temperature_heatmap, weather):
    weather_timeseries = weather[["temperature_degF", "humidity_pc"]].plot(
        grid=True, figsize=(10, 6), title=county_st
    )
    mo.ui.tabs(
        {
            "Plot": weather_timeseries,
            "Temperature": temperature_heatmap,
            "Humidity": humidity_heatmap,
            "Data": weather,
        },
        lazy=True,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The estimator has several tunable parameters. These have been tested for WECC and on average the following values have been found to be best overall. However you may explore different values to see if they yield a better result for any given hold-out test.
    """)
    return


@app.cell
def _(mo):
    harmonics_year = mo.ui.number(label="Yearly:",value=4,start=2,debounce=True)
    harmonics_week = mo.ui.number(label="Weekly:",value=4,start=2,debounce=True)
    harmonics_day = mo.ui.number(label="Daily:",value=6,start=2,debounce=True)
    return harmonics_day, harmonics_week, harmonics_year


@app.cell
def _(harmonics_day, harmonics_week, harmonics_year, mo):
    take_log = mo.ui.switch(label='Take log of target data', value=True)
    use_ar = mo.ui.switch(label='Use AR model', value=False)
    use_outlier = mo.ui.switch(label='Use outlier detector', value=False)
    outlier_reg_weight = mo.ui.slider(0.0001, 2.0, step=0.0001, value=1e-4, label='Outlier L1 reg weight')
    outlier_threshold = mo.ui.slider(0.001, 0.5, step=0.001, value=0.05, label='Outlier threshold (log space)')
    solver_select = mo.ui.dropdown(['CLARABEL', 'MOSEK'], value='CLARABEL', label='Solver')
    verbose = mo.ui.switch(label='Verbose solver output', value=True)
    fit_model = mo.ui.run_button(label='Fit Model')

    mo.vstack([
        mo.hstack([take_log, use_ar, use_outlier]),
        mo.hstack([outlier_reg_weight, outlier_threshold]),
        mo.hstack([solver_select, verbose]),
        mo.hstack([mo.md("Harmonics:"),harmonics_year,harmonics_week,harmonics_day]),
    ])
    return (
        fit_model,
        outlier_reg_weight,
        solver_select,
        take_log,
        use_ar,
        use_outlier,
        verbose,
    )


@app.cell
def _():
    return


@app.cell
def _(enduse_mw, holdout, pd, tot, training, weather):
    # Prepare exogenous variables (weather features)
    # Use selected weather columns
    weather_cols = ['temperature_degF', 'humidity_pc']
    _data = pd.concat([tot[enduse_mw],weather[weather_cols]],axis=1)
    df_train = _data.loc[training]
    df_test = _data.loc[holdout]

    # Ensure we have at least one column
    if len(weather_cols) == 0:
        print("Warning: No exogenous variables selected. Using temperature_degF as default.")
        weather_cols = ['temperature_degF'] if 'temperature_degF' in df_train.columns else list(df_train.columns)[:1]

    # Create X_train and X_test
    X_train = df_train[weather_cols].copy()
    X_test = df_test[weather_cols].copy()

    # Find valid samples (no NaN in target or weather data)
    train_valid = ~(df_train[enduse_mw].isna() | X_train.isna().any(axis=1))
    test_valid = ~(df_test[enduse_mw].isna() | X_test.isna().any(axis=1))

    # Filter to valid samples
    X_train = X_train[train_valid]
    X_test = X_test[test_valid]

    y_train_aligned = df_train[enduse_mw].loc[X_train.index].values
    y_test_aligned = df_test[enduse_mw].loc[X_test.index].values

    timestamps_train_aligned = X_train.index
    timestamps_test_aligned = X_test.index

    print(f"X_train shape: {X_train.shape}")
    print(f"X_test shape: {X_test.shape}")
    print(f"y_train aligned: {len(y_train_aligned)} samples")
    print(f"y_test aligned: {len(y_test_aligned)} samples")
    print(f"\nExogenous variables: {list(X_train.columns)}")
    return X_train, y_train_aligned


@app.cell
def _(
    PERIOD_HOURLY_DAILY,
    PERIOD_HOURLY_WEEKLY,
    PERIOD_HOURLY_YEARLY,
    TsgamArConfig,
    TsgamEstimator,
    TsgamEstimatorConfig,
    TsgamMultiPeriodicConfig,
    TsgamOutlierConfig,
    TsgamSolverConfig,
    TsgamSplineConfig,
    X_train,
    fit_model,
    mo,
    np,
    outlier_reg_weight,
    solver_select,
    take_log,
    use_ar,
    use_outlier,
    verbose,
    y_train_aligned,
):
    if fit_model.value:

        # Apply log transform if requested
        if take_log.value:
            y_train_log = np.log(y_train_aligned + 1.0)
            print("Applied log transform to target")
        else:
            y_train_log = y_train_aligned.copy()
    
        # Multi-periodic Fourier configuration
        # For one year of data, we use yearly, weekly, and daily periods
        multi_periodic_config = TsgamMultiPeriodicConfig(
            num_harmonics=[4, 4, 6],  # yearly, weekly, daily
            periods=[PERIOD_HOURLY_YEARLY, PERIOD_HOURLY_WEEKLY, PERIOD_HOURLY_DAILY],
            reg_weight=6e-5
        )
    
        print(f"Multi-periodic config: {multi_periodic_config.num_harmonics} harmonics for periods {multi_periodic_config.periods}")
    
        # Exogenous variables configuration
        # Order must match the order of columns in X_train/X_test
        exog_config = []
    
        # Define configurations for each weather variable
        var_configs = {
            'temperature_degF': TsgamSplineConfig(
                n_knots=10,
                lags=[-3, -2, -1, 0],  # Current and 1-3 hours back
                reg_weight=6e-5,
                diff_reg_weight=0.5
            ),
            'humidity_pc': TsgamSplineConfig(
                n_knots=8,
                lags=[-2, -1, 0],  # Current and 1-2 hours back
                reg_weight=6e-5,
                diff_reg_weight=0.5
            ),
            'global_Wpms': TsgamSplineConfig(
                n_knots=8,
                lags=[-1, 0],
                reg_weight=6e-5,
                diff_reg_weight=0.5
            ),
            'direct_Wpms': TsgamSplineConfig(
                n_knots=8,
                lags=[-1, 0],
                reg_weight=6e-5,
                diff_reg_weight=0.5
            ),
            'diffuse_Wpms': TsgamSplineConfig(
                n_knots=8,
                lags=[-1, 0],
                reg_weight=6e-5,
                diff_reg_weight=0.5
            ),
        }
    
        # Build exog_config based on X_train columns
        print(f"X_train columns: {list(X_train.columns)}")
        for var_name in X_train.columns:
            if var_name in var_configs:
                exog_config.append(var_configs[var_name])
            else:
                # Fallback configuration for unknown variables
                exog_config.append(TsgamSplineConfig(
                    n_knots=8,
                    lags=[0],
                    reg_weight=6e-5,
                    diff_reg_weight=0.5
                ))
    
        print(f"exog_config length: {len(exog_config)}")
    
        # AR configuration
        ar_config = None
        if use_ar.value:
            ar_config = TsgamArConfig(
                lags=[1, 2, 3, 4],
                l1_constraint=0.97
            )
    
        # Outlier detector configuration
        outlier_config = None
        if use_outlier.value:
            outlier_config = TsgamOutlierConfig(
                reg_weight=outlier_reg_weight.value,
                period_hours=24.0  # Daily outliers
            )
    
        # Solver configuration
        solver_config = TsgamSolverConfig(
            solver=solver_select.value,
            verbose=verbose.value
        )
    
        # Create main config
        config = TsgamEstimatorConfig(
            multi_periodic_config=multi_periodic_config,
            exog_config=exog_config,
            ar_config=ar_config,
            outlier_config=outlier_config,
            solver_config=solver_config,
            random_state=42
        )
    
        # Create and fit estimator
        print("\nCreating and fitting TSGAM estimator...")
        print(f"Training data has {len(X_train)} samples with gaps (missing last week of each month)")
        estimator = TsgamEstimator(config=config)
    
        print("Fitting model (this may take a few minutes)...")
        estimator.fit(X_train, y_train_log)
    
        print("\nModel fitting complete!")
        print(f"Problem status: {estimator.decomposition_['status']}")
        if estimator.decomposition_["status"] in ["optimal", "optimal_inaccurate"]:
            print(f"Optimal value: {estimator.decomposition_['problem'].value:.6e}")
    
        if getattr(estimator, "ar_coef_", None) is not None:
            print("\nAR model fitted successfully:")
            print(f"  AR coefficients: {estimator.ar_coef_}")
            print(f"  AR intercept: {estimator.ar_intercept_:.6f}")

    mo.md(f"Press {fit_model} to run load estimate")

    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    from tsgam_estimator import (
        TsgamEstimator,
        TsgamEstimatorConfig,
        TsgamMultiPeriodicConfig,
        TsgamSplineConfig,
        TsgamArConfig,
        TsgamOutlierConfig,
        TsgamSolverConfig,
        PERIOD_HOURLY_DAILY,
        PERIOD_HOURLY_WEEKLY,
        PERIOD_HOURLY_YEARLY
    )
    from loads.residential import Residential
    from loads.commercial import Commercial
    from loads.industry import Industry
    from loads.agriculture import Agriculture
    from weather import Weather

    return (
        Agriculture,
        Commercial,
        Industry,
        PERIOD_HOURLY_DAILY,
        PERIOD_HOURLY_WEEKLY,
        PERIOD_HOURLY_YEARLY,
        Residential,
        TsgamArConfig,
        TsgamEstimator,
        TsgamEstimatorConfig,
        TsgamMultiPeriodicConfig,
        TsgamOutlierConfig,
        TsgamSolverConfig,
        TsgamSplineConfig,
        Weather,
        mo,
        np,
        pd,
        plt,
    )


if __name__ == "__main__":
    app.run()
