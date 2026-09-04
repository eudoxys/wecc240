"""Load calibration

Description
-----------

This module enables calibration of load data based on two types of constraints.

- **Energy**: the row sums match the target total energy

- **Power**: the maximum of the column sums match the target peak power

Target can be specified as one of the following:

1. `None`: The target is the existing value taken from the data.

2. `float`: The target is evaluated over all the columns of the data.

3. `list`: The target is different for multiple column groups in the data. In
this case each member of the target list is specified as a tuple with a list
of column indexes and a float specifying the target for that column group.
Note that there is no requirement that the columns be exclusive to a target
but specifying a column in multiple targets may create an infeasible
problem.

Example
-------

This example rescales the node_total.csv data so that the energy is 10% higher
and peak load is 30% lower.

    data = pd.read_csv("node_total.csv",index_col=[0],parse_dates[0])
    result,problem = node_calibrate(data,E_target=1.1,P_target=0.9)
    scale = get_variable(problem,"s")
    offset = get_variable(problem,"b")
    print(f"{s=:4f}, {b=:.4f}")
"""

from time import time

import numpy as np
import cvxpy as cp

def cvx_options(**kwargs) -> dict:
    """Specify default cvx problem options
    
    Arguments
    ---------
    - `**kwargs`: modifications to default applied to this option set

    Examples
    --------

    To get the default `cvxpy.Problem.solve` options use the following.

        cvx_options()

    To get the default options with the "highs" solver use the following.

        cvx_options(solver="highs")

    To get the default optios with an interation limit of 50000 use the
    following.

        cvx_options(max_iter=50000)
    """
    options = {
        "solver": "clarabel",
        "verbose": True,
    }
    options.update(kwargs)
    return options

def _iterable(x):
    """Check if object is iterable"""
    return hasattr(x,"__iter__")

def _check_target(
    target:float|list[tuple[list[int],float]]|None,
    default:float,
    ) -> float|list[tuple[list[int],float]]:
    """Check the target value(s)

    Arguments
    ---------

    - `target`: the target value(s) to check

    - `default`: the default value to use when the target is `None`

    Returns
    -------

    - `float|list[tuple[list[int],float]]`: the checked value to use or the
      default value
    """
    if target is None: # target is None
        target = default
    elif _iterable(target): # target is iterable
        for n,x in enumerate(target):
            assert _iterable(x[0]), f"target {n} must be iterable"
            assert all([isinstance(y,int) for y in x[0]]), f"all members of {n=} must be int"
            assert isinstance(x[1],float)
        return target

    # target must be float
    assert isinstance(target,float)

    return target

def constant_or_parameter(name:str,data:np.array,parameters:list[str],nonneg,**kwargs):
    if name in parameters:
        return cp.Parameter(shape=data.shape,value=data,name=name,nonneg=nonneg,**kwargs)
    return cp.Constant(data,name=name,**kwargs)

def calibrate(
    X_raw: np.array,
    D_raw: np.array,
    state_groups: dict,
    g_caiso, g_wecc: np.array,
    E_state: dict,
    P_caiso_raw, P_wecc_raw: float,
    *,
    gamma:float=None,
    mu:float=None,
    lam:float=None,
    eps:float=1e-6,
    options:dict=cvx_options(),
    parameters:list[str]=None,
    problem:cp.Problem=None,
    ) -> [float,cp.Problem]:
    """Solve the sum/max target problem using scale and offset

    Arguments
    ---------
    
    - `X_raw`: (T, n) nonnegative simulated LOAD per unit (controllable)
    
    - `D_raw`: (T, n) nonnegative fixed distributed generation per unit
      (locked), e.g., `load = X_raw - D_raw`
    
    - `state_groups`: dict {state: g_k} each g_k in [0,1]^n, sum_k g_k = 1
      (partition) boolean for counties (typically); fractional for nodes
    
    - `E_state` : dict {state: E_k_raw} per-state NET-LOAD energy targets
    
    - `g_caiso, g_wecc` : (n,) in [0,1] fractional membership (g_caiso <=
      g_wecc)
    
    - `P_caiso_raw, P_wecc_raw` : NET-LOAD peak power target

    - `gamma`: shape fidelity (anti-crushing) -- primary regularizer
    
    - `mu`: (n,) `E_target` objective hyperparameters (recovers `E_target`
      equalities for states) 
    
    - `lam`: (2,) `P_target` objective hyperparameters for WECC and CAISO
      (presses `P_target` to max)
    
    - `eps`: small symmetric reduce to guarantee a unique solution when zero
      or constant columns are present
    
    - `options`: CVX options (see `cvx_options`)

    - `parameters`: list of constant to parameterize

    Returns
    -------

    - `dict`: result of optimization
        - `scale`: the scale value
        - `offset`: the offset value
        - `value`: the optimization cost function value
        - `problem`: the optimization problem object

    Description
    -----------

    This solver scales and offsets the columns of the array `X_raw` such that
    the total of the columns match `E_state` and the maximum across the rows
    of the sums of the rows matches `P_caiso_raw` and P_wecc_raw`. Since
    exact matching of both is typically infeasible, the solver uses the
    hyper-parameters `mu` and `lam` to prioritize these against the fidelity
    to the overall shape of `X`, which is controlled by the primary
    regularizer `gamma`. The hyper-parameters `mu` and `lam` work as
    follows.

    - `mu`: controls how strongly the solver recovers `E_target`.

    - `lam`: controls how strongly the solver recover `P_target`.

    The hyper-parameter `eps` is used to guarantee a unique solution when one
    or more zero or constant columns are present in `X_raw`. 
    """

    if not problem is None:
      get_parameter(problem,"gamma").value = np.array([gamma])
      get_parameter(problem,"mu").value = np.array(mu)
      get_parameter(problem,"lam").value = np.array(lam)
      value = problem.solve()

      return {
        "scale": get_variable(problem,"s"),
        "offset": get_variable(problem,"b") * X_raw.max(),
        "value": value,
        "problem": problem,
        }

    T, n = X_raw.shape

    if parameters is None:
        parameters = []

    # Global max-scaling on LOAD; express DG in the SAME normalized units.
    c = X_raw.max()
    X = X_raw / c
    D = D_raw / c

    a = X.sum(axis=0)          # (n,) per-unit LOAD energy weights (normalized)
    d = D.sum(axis=0)          # (n,) per-unit DG energy (normalized, constant)
    col_min = X.min(axis=0)    # (n,) per-unit LOAD minima (for nonnegativity)

    # Targets -> normalized domain
    E_target = {k: E_state[k] / c for k in state_groups}
    P_caiso  = P_caiso_raw / c
    P_wecc   = P_wecc_raw  / c

    # Decision variables (LOAD only)
    # EDIT: added names for variables
    s = cp.Variable(n, nonneg=True, name='s')   # per-unit load scalings
    b = cp.Variable(n, name='b')                # per-unit load offsets

    # Shaped LOAD: L[t,j] = s_j X[t,j] + b_j.  Shaped NET load: N = L - D.
    # EDIT: added "C" to reshape per warning from cvxpy
    L = cp.multiply(X, cp.reshape(s, (1, n), "C")) + cp.reshape(b, (1, n), "C")

    # --- Objective terms ---------------------------------------------------------
    # Load shape fidelity (on the controllable load; DG excluded)
    shape_dev = cp.sum_squares(L - X)

    # Per-state NET-LOAD energy fidelity (soft; partitioned -> non-competing)
    #   E_g = (g*a) @ s + T*(g @ b) - (g @ d)      [DG total g@d is a constant]
    energy_pen = 0

    # EDIT: mu is passed in and scale by the number of hours
    # ISSUE: parameter fails DCP test
    if mu is None:
        mu = {k:T for k in state_groups}
    else:
        mu = constant_or_parameter(data=mu,name='mu',parameters=parameters,nonneg=True) * T
    for k, g in state_groups.items():
        E_g = (g * a) @ s + T * (g @ b) - (g @ d)
        energy_pen = energy_pen + mu[k] * cp.square(E_g/E_target[k] - 1)

    # Region-weighted power drive (nested CAISO shell vs. WECC remainder)
    # EDIT: lam is passed in as (2,) array for CAISO and WECC and scaled by the number of units
    if lam is None:
        lam = [n,n]
    else:
        lam = constant_or_parameter(data=lam,name='lam',parameters=parameters,nonneg=True) * n
    g_wecc_only = g_wecc - g_caiso
    drive = lam[0] * (g_caiso @ b) + lam[1] * (g_wecc_only @ b)

    # Well-posedness ridge
    eps = cp.Constant(eps,name='eps')
    ridge = eps * (cp.sum_squares(s - 1) + cp.sum_squares(b))

    # EDIT: gamma is passed in and scaled by size of data
    # ISSUE: parameter fails DCP test
    if gamma is None:
        gamma = n * T
    else:
        gamma = constant_or_parameter(data=np.array([gamma]), name='gamma', parameters=parameters, nonneg=True) * n * T
    objective = cp.Minimize(gamma * shape_dev + energy_pen - drive + ridge)

    # --- Constraints -------------------------------------------------------------
    # NET-LOAD group peaks: max_t [ (X_g s)_t + g@b - (D_g)_t ]
    Xg_caiso = X * g_caiso[None, :]
    Xg_wecc  = X * g_wecc[None, :]
    Dg_caiso = D @ g_caiso            # (T,) fixed DG profile for CAISO
    Dg_wecc  = D @ g_wecc             # (T,) fixed DG profile for WECC

    peak_caiso = cp.max(Xg_caiso @ s + (g_caiso @ b) - Dg_caiso)
    peak_wecc  = cp.max(Xg_wecc  @ s + (g_wecc  @ b) - Dg_wecc)

    constraints = [
        peak_caiso <= P_caiso,                     # CAISO net-load peak (driven tight)
        peak_wecc  <= P_wecc,                      # WECC  net-load peak (driven tight)
        cp.multiply(s, col_min) + b >= 0,          # LOAD nonnegativity (reduced form)
        # equivalent full form: L >= 0   (net load N may be negative under high DG)
    ]

    problem = cp.Problem(objective, constraints)
    assert problem.is_dcp(), "ERROR: problem is no DCP"
    # EDIT: save value for return
    value = problem.solve(**options)

    # diagnostic output if cvx_options includes `verbose=True`
    if "verbose" in options and options["verbose"]:
        target_energy = sum(x for x in E_target.values())
        target_power = P_caiso + P_wecc
        if problem.status not in ("infeasible", "unbounded"):
            L_val = X * s.value[None, :] + b.value[None, :] # shaped load (normalized)
            N_val = L_val - D # shaped net load
            L_raw = c * L_val
            N_raw = c * N_val
            ach_P_caiso = c * np.max((X * g_caiso[None, :]) @ s.value + (g_caiso @ b.value) - (D @ g_caiso))
            ach_P_wecc = c * np.max((X * g_wecc[None, :]) @ s.value + (g_wecc @ b.value) - (D @ g_wecc))
            print("CAISO net-load peak:", ach_P_caiso, " target:", P_caiso_raw, " tight?", (constraints[0].dual_value or 0) > 1e-9)
            print("WECC net-load peak:", ach_P_wecc, " target:", P_wecc_raw, " tight?", (constraints[1].dual_value or 0) > 1e-9)
            print("load min :", L_raw.min(), "(should be >= 0)")
            print("net-load min:", N_raw.min(), "(may be < 0 under high DG)")
            for k, g in state_groups.items():
                E_ach = c * ((g * a) @ s.value + T * (g @ b.value) - (g @ d))
                print(f" {k:>6d} net-load energy: {E_ach:12.3f}"
                  f" target {E_state[k]:12.3f} miss {E_ach - E_state[k]:+.3f}")
        else:
            print("Problem status:", problem.status)

    return {
        "scale": s.value,
        "offset": b.value * c,
        "value": value,
        "problem": problem,
        }

def get_scalar(
    problem:cp.Problem,
    name:str) -> float:
    """Read scalar from problem data"""
    for const in problem.constants():
        if const.name() == name:
            return float(const.value)
    raise ValueError(f"{name=} not found")

def get_variable(
    problem:cp.Problem,
    name:str) -> np.array:
    """Read variable from problem data"""
    for var in problem.variables():
        if var.name() == name:
            return var.value

def get_parameter(
    problem:cp.Problem,
    name:str) -> np.array:
    """Read variable from problem data"""
    for param in problem.parameters():
        if param.name() == name:
            return param

def get_vector(
    problem:cp.Problem,
    name:str) -> float:
    """Read scalar from problem data"""
    for vector in problem.constants():
        if vector.name() == name:
            return np.array(vector.value)
    raise ValueError(f"{name=} not found")

def evaluate(
    s, b:np.array,
    X,D: np.array,
    state_groups: dict,
    g_caiso, g_wecc: np.array,
    E_state: dict,
    P_caiso, P_wecc: float,
    ):
    """Apply scale and offset to data and evaluate errors

    Arguments
    ---------

    - `data`: original dataframe of unit (county or node) data
    - `scale`: power scale to apply to data
    - `offset`: power offset to apply to data
    - `E_state`: unit energy targets
    - `P_target`: group power targets
    - `P_groups`: group indexes for each target
    
    Returns
    -------
    - `result`: result of applying scale and offset to data
    - `energy_rmse`: energy rmse of each unit
    - `power_rmse`: power rmse of each group
    - `shape_rmse`: shape change rms
    """

    T, n = X.shape

    # load shape deviation
    L = X * s + b
    shape_dev = float(np.linalg.norm( L - X,2))

    # energy deviation
    E_target = {k: E_state[k] for k in state_groups}
    a = X.sum(axis=0)
    d = D.sum(axis=0)
    energy_dev = []
    for k,g in state_groups.items():
        E_g = (g * a) @ s + T * ( g @ b ) - ( g @ d )
        energy_dev.append(E_g - E_target[k])

    # --- Constraints -------------------------------------------------------------
    # NET-LOAD group peaks: max_t [ (X_g s)_t + g@b - (D_g)_t ]
    Xg_caiso = X * g_caiso[None, :]
    Xg_wecc  = X * g_wecc[None, :]
    Dg_caiso = D @ g_caiso            # (T,) fixed DG profile for CAISO
    Dg_wecc  = D @ g_wecc             # (T,) fixed DG profile for WECC

    peak_caiso = float(np.max(Xg_caiso @ s + (g_caiso @ b) - Dg_caiso))
    peak_wecc  = float(np.max(Xg_wecc  @ s + (g_wecc  @ b) - Dg_wecc))
    peak_dev = [peak_caiso-P_caiso,peak_wecc-P_wecc]

    return L,np.array(energy_dev),np.array(peak_dev),shape_dev

if __name__ == "__main__":

    import os
    import datetime
    import pandas as pd
    import warnings
    from fips import Counties

    # warnings.simplefilter('error')
    options = cvx_options(verbose=False)

    dt = pd.date_range(
        start=f"2020-08-01 00:00:00+0000",
        end=f"2020-08-31 23:59:59+0000",
        freq="1h"
        )
    
    # read county-level total loads
    county_total = pd.read_csv("county_total.csv", index_col=[0], parse_dates=[0])
    county_dg = pd.read_csv("county_dg.csv", index_col=[0], parse_dates=[0])
    assert set(county_total.columns) == set(county_dg.columns), "total and DG counties do not match"
    county_ndx = {x:n for n,x in enumerate(county_total.columns)} # index into load data columns

    # read county GIS data
    counties = Counties(use_index="SYSTEM",selection="WECC",set_index="REGION")
    counties["COUNTY_ST"] = [f"{x} {y}" for x,y in counties[["COUNTY","ST"]].values]
    counties["COUNTY_NDX"] = [county_ndx[x] if x in county_ndx else -1 for x in counties["COUNTY_ST"].values]
    counties.drop(counties[counties["COUNTY_NDX"]==-1].index,inplace=True,axis=0)

    # read state energy targets
    state_cf = pd.read_csv("state_cf.csv",index_col=[0],parse_dates=[0])
    wecc_cf = state_cf[county_total.columns]
    wecc_cf = wecc_cf.rename({x:x.split()[-1] for x in state_cf.columns},axis=1).T.groupby(level=0).sum().T.stack()
    state_mwh = pd.read_csv("state_mwh.csv",index_col=[0,1],parse_dates=[0])

    # read regional peak loads
    peak_load = pd.read_csv("peak_load.csv",index_col=[1,0],parse_dates=[0])

    # prepare problem data
    county_names = county_total.columns
    state_ndx = {y:n for n,y in enumerate(sorted(set(x.split()[-1] for x in county_names)))}
    X = county_total.loc[dt,:].values
    D = county_dg.loc[dt,:].values
    state_groups = {
        m:[1 if c.split()[-1]==n else 0 for c in county_names] 
        for n,m in state_ndx.items()
        }
    g_wecc = [1.0 for x in county_total.columns]
    counties_caiso = set(counties.loc["CAISO","COUNTY_ST"].values)
    g_caiso = [1.0 if x in counties_caiso else 0.0 for x in county_total.columns]
    pd.DataFrame(
        data={
        "CAISO": g_caiso,
        "WECC": g_wecc,
        },
        index=county_total.columns,
        ).to_csv("state_groups.csv",index=True,header=True)

    dt_month = dt[0].to_pydatetime()
    assert (dt_month.day==1 and dt_month.hour==0), "data must begin with first hour of month"
    E_target = state_mwh["load"] * wecc_cf
    E_target.unstack("state").round(3).to_csv("energy_target.csv",index=True,header=True)

    E_state = {state_ndx[x]:y for x,y in E_target.loc[dt_month].to_dict().items()}
    P_wecc_raw = peak_load.loc["WECC"].resample("MS").ffill()["peak_mw"]
    P_caiso_raw = peak_load.loc["CAISO"].resample("MS").ffill()["peak_mw"]
    pd.DataFrame(
        data={
        "CAISO": P_caiso_raw,
        "WECC": P_wecc_raw,
        },
        index=P_wecc_raw.index,
        ).to_csv("peak_target.csv",index=True,header=True)

    results = []

    for gamma in [10**n for n in range(-3,3)]:
        for mu in [10**n for n in range(-3,3)]:
            problem = None
            for lam in [10**n for n in range(-3,3)]:
                print(f"Processing {gamma=}, {mu=}, {lam=}",end="...",flush=True)

                params = {
                    "gamma": gamma,
                    "mu": np.array([mu]*len(state_ndx)),
                    "lam": np.array([lam]*2),
                    "eps": 1e-6,
                }

                # solve calibration problem
                try:
                    tic = time()
                    if problem is None:
                            result = calibrate(
                                X, D,
                                state_groups, 
                                np.array(g_caiso), np.array(g_wecc), 
                                E_state,
                                P_caiso_raw.loc[dt_month], P_wecc_raw.loc[dt_month],
                                options=cvx_options(**options),
                                **params,
                                parameters=["gamma","mu","lam"],
                                )
                            scale = result["scale"]
                            offset = result["offset"]
                            problem = result["problem"]
                    else:
                        get_parameter(problem,"lam").value = np.array([lam]*2)
                        problem.solve()
                        scale = get_variable(problem,"s")
                        offset = get_variable(problem,"b") * X.max()
                    toc = time()

                    L,energy_dev,power_dev,shape_dev = evaluate(
                        scale, offset,
                        X, D,
                        state_groups, np.array(g_caiso), np.array(g_wecc), 
                        E_state,
                        P_caiso_raw.loc[dt_month], P_wecc_raw.loc[dt_month],
                        )

                    row = {
                        "gamma": [gamma],
                        "mu": [mu],
                        "lam": [lam],
                        "eps": [params["eps"]],
                        "status": problem.status,
                        "time": round(toc-tic,3),
                    }
                    row["E_rmse"] = round(np.linalg.norm(L-X,2)/1e6,3)
                    row["P_caiso"] = round(power_dev[0]/1e3,3)
                    row["P_wecc"] = round(power_dev[1]/1e3,3)
                    row["S_dev"] = round(shape_dev/1e3,3)
                    for state,k in state_ndx.items():
                        row[f"E_{state}"] = round(energy_dev[k]/1e6,3)
                except Exception as err:
                    row = {
                        "gamma": [gamma],
                        "mu": [mu],
                        "lam": [lam],
                        "eps": [params["eps"]],
                        "status": problem.status,
                    }

                results.append(pd.DataFrame(data=row,index=[len(results)]))

                report = pd.concat(results).set_index(["gamma","mu","lam","eps"])
                report.to_csv("load_calibrate.csv",index=True,header=True)

                print("ok")

    print(report)