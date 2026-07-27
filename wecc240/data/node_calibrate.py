# Setup and solve the problem
# Set the default cvxpy solve options
import numpy as np
import cvxpy as cp

def cvx_options(**kwargs):
    """Specify default cvx problem options
    
    Arguments
    ---------
    - `**kwargs`: modifications to default to appy to this option set

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

def _check_target(
    target:float|list[tuple[list[int],float]],
    default:float,
    ):
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
    if target is None:
        target = default
    elif hasattr(target,"__iter__"):
        for n,x in enumerate(target):
            assert hasattr(x[0],"__iter__"), f"target {n} must be iterable"
            assert all([isinstance(y,int) for y in x[0]]), f"all members of {n=} must be int"
            assert isinstance(x[1],float)
        return target
    assert isinstance(target,float)
    return target

def calibrate(X:np.array,
            E_target:float|list[tuple[list[int],float]]=None,
            P_target:float|list[tuple[list[int],float]]=None,
            *,
            gamma:float=1000.0,
            mu:float=1.0,
            lam:float=0.0,
            eps:float=1e-6,
            options:dict=cvx_options(),
            ):
    """Solve the sum/max target problem using scale and offset

    Arguments
    ---------
    - `X(T, n)`: nonnegative array of time-series signals
    - `E_target`: scalar sum of rows target(s)
    - `P_target`: scalar max of sum columns target(s)
    - `gamma`: shape fidelity (anti-crushing) -- primary regularizer
    - `mu`: `E_target` objective hyperparameter (recovers `E_target` equality)   
    - `lam`: `P_target` objective hyperparameter (presses `P_target` to max)
    - `eps`: small symmetric reduce guaranteed a unique solution when zero or
      constant columns are present
    - `options`: CVX options (see `cvx_options`)

    Description
    -----------

    This solver scales and offsets the array X such that the total of the cells
    matches `E_target` and the maximum across the rows of the sums of the rows
    matches `P_target`. Since exact matching of both is typically infeasible, 
    the solver uses the hyper-parameters `mu` and `lam` to prioritize these
    against the fidelity to the overall shape of `X`, which is controlled by the
    primary regularizer `gamma`. The hyper-parameters `mu` and `lam` work as
    follows.

    - `mu`: controls how strongly the solver recovers `E_target`.

    - `lam`: controls how strongly the solver recover `P_target`.

    The hyper-parameter `eps` is used to guarantee
    a unique solution when a zero or constant column is present in `X`. 

    If the value of `E_target` is `None`, the sum of the cells is used as the 
    default. If the value of `P_target` is `None`. The maximum of the sums of
    all columns is used as the default.

    When multiple `E_target` or `P_target` objectives are sought, these can be
    specified as a list of columns with the target value, e.g.,

        [([1,2,3], 1.23),
         ([4,5,6], 4.56),
         ]

    Note that a column may appear in more than one target if desired.
    """

    E_target = _check_target(E_target,np.sum(X))
    P_target = _check_target(P_target,np.max(np.sum(X,axis=1)))

    T, n = X.shape

    c = cp.Constant(X.min(axis=0),name='c')     # per-column minima (for output nonneg reduction)
    E = cp.Constant(E_target,name='E')          # total energy target scalar
    if hasattr(P_target,"__iter__"):            # peak power target scalar
        P = cp.Constant([x[1] for x in P_target],name='P')
    else:
        P = cp.Constant(P_target,name='P')      

    s = cp.Variable(n, nonneg=True, name='s')   # per-column scaling factors
    b = cp.Variable(n, name='b')                # per-column offsets

    # Output signal: column j is s_j * X[:,j] + b_j (broadcast over rows)
    Y = cp.multiply(X, 
            cp.reshape(s, (1, n),order='C')) + cp.reshape(b, (1, n),order='C')

    peak = cp.max(cp.sum(Y, axis=1))            # max row-sum of OUTPUT (convex)
    csum = cp.sum(Y,axis=1)
    energy = cp.sum(Y)                          # total energy of OUTPUT (affine)

    mu = cp.Constant(mu,name='mu')
    lam = cp.Constant(lam,name='lam')
    gamma = cp.Constant(gamma,name='gamma')
    eps = cp.Constant(eps,name='eps')

    objective = cp.Minimize(
        gamma * cp.sum_squares(Y - X) / T**2    # == ||X diag(s) + 1 b^T - X||_F^2
        + mu * cp.square(energy - E) / T**2
        - lam * cp.sum(b) / n
        + eps * (cp.sum_squares(s - 1) + cp.sum_squares(b))
    )

    if hasattr(P_target,"__iter__"):
        constraints = []
        for n,x in P_target:
            constraints.append(cp.max(csum[n]) <= x)
    else:
        constraints = [peak <= P]                    # power inequality (convex relaxation)
        
    constraints.append(cp.multiply(s, c) + b >= 0)  # output nonnegativity (reduced form)
                                                    # equivalent full form: Y >= 0

    problem = cp.Problem(objective, constraints)
    assert problem.is_dcp(), "ERROR: problem is not DCP"
    result = problem.solve(**options)

    if "verbose" in options and options["verbose"]:
        if problem.status not in ("infeasible", "unbounded"):
            scale = s.value.round(4)
            offset = b.value.round(3)
            Y_val = X * s.value[None, :] + b.value[None, :]
            achieved_power = np.max(Y_val.sum(axis=1))
            achieved_energy = Y_val.sum()
            mu_power = constraints[0].dual_value # > 0 => power target met exactly
            print("scaling factors :", s.value)
            print("offsets :", b.value)
            print("achieved energy :", achieved_energy, " target:", E_target,
            " (miss:", achieved_energy - E_target, ")")
            print("achieved power :", achieved_power, " target:", P_target,
            " tight?", mu_power is not None and mu_power > 1e-9)
            print("output min :", Y_val.min(), "(should be >= 0)")
            # Diagnostic: per-column deviation; largest-energy column should move least.
            print("per-column dev :", np.sum((Y_val - X) ** 2, axis=0))    
        else:
            print("Problem status:", problem.status)

    return result,problem

def get_scalar(problem,name):
    """Read scalar from problem data"""
    for const in problem.constants():
        if const.name() == name:
            return float(const.value)
    raise ValueError(f"{name=} not found")

def get_variable(problem,name):
    """Read variable from problem data"""
    for var in problem.variables():
        if var.name() == name:
            return var.value

if __name__ == "__main__":

    import os
    import pandas as pd
    import warnings
    from fips import Counties

    # warnings.simplefilter('error')
    options = cvx_options(verbose=False)

    # print("Testing identity problem over all months of node data",end="",flush=True)

    # # load county/state node mapping
    # county_node_map = pd.read_csv(
    #     "county_node_map.csv",
    #     index_col=[0],
    #     usecols=["county_st","load"],
    #     )
    # county_node_map.columns = ["node"]
    # county_node_map["state"] = [x.split()[-1] for x in county_node_map.index]
    # state_node_map = county_node_map.reset_index().set_index("state")
    # # for state in state_node_map.index.unique():
    # #     print(state,state_node_map.loc[state,"node"].to_list())
    # filename = "node_total.csv"
    # node_total = pd.read_csv(filename, index_col=[0], parse_dates=[0])
    # missing = set(node_total.columns) - set(county_node_map.node)
    # assert missing == set(), f"county_total.csv: {missing=} not in the county_node_map.csv"

    # for me in pd.date_range(start=node_total.index.min(),end=node_total.index.max(),freq="ME"):
    #     print(".",end="",flush=True)
    #     year,month,lastday = me.year,me.month,me.day
    #     dt = pd.date_range(
    #         start=f"{year}-{month:02d}-01 00:00:00+0000",
    #         end=f"{year}-{month:02d}-{lastday} 23:59:59+0000",
    #         freq="1h"
    #         )
    #     X = node_total.loc[dt,:].dropna().values
    #     X /= X.sum(axis=1).max()
    #     E = np.sum(X)
    #     P = np.max(np.sum(X,axis=1))
    #     result,problem = calibrate(X,
    #         options=cvx_options(**options),
    #         )
    #     s = get_variable(problem,'s')
    #     b = get_variable(problem,'b')
    #     assert (s.round(2)==1.0).all()
    #     assert (b.round(2)==0.0).all()
    # print("ok")


    print("Testing full problem on mu sweep of August 2020 county data",end="",flush=True)

    # read county-level total loads
    filename = "county_total.csv.gz"
    county_total = pd.read_csv(filename, index_col=[0], parse_dates=[0])
    county_ndx = {x:n for n,x in enumerate(county_total.columns)} # index into load data columns

    # read county GIS data
    counties = Counties(use_index="SYSTEM",selection="WECC",set_index="REGION")
    counties["COUNTY_ST"] = [f"{x} {y}" for x,y in counties[["COUNTY","ST"]].values]
    counties["COUNTY_NDX"] = [county_ndx[x] if x in county_ndx else -1 for x in counties["COUNTY_ST"].values]
    counties.drop(counties[counties["COUNTY_NDX"]==-1].index,inplace=True,axis=0)
    peaks = [ # peak target values for regions
        (counties.loc["CAISO"]["COUNTY_NDX"].astype(int).to_list(),45.0), # TODO: get exact value for Aug 2020 in CAISO
        (counties["COUNTY_NDX"].astype(int).to_list(),167.0), # TODO: get exact value for Aug 2020 in WECC
    ]

    dt = pd.date_range(
        start=f"2020-08-01 00:00:00+0000",
        end=f"2020-08-31 23:59:59+0000",
        freq="1h"
        )
    for mu in [0] + sorted([x*y for x in [1,2,5] for y in [10**n for n in range(-2,5)]]):
        print(".",end="",flush=True)
        X = county_total.loc[dt,:].dropna().values
        X /= X.sum(axis=1).max()
        E = np.sum(X)
        P = np.max(np.sum(X,axis=1))
        result,problem = calibrate(X,
            P_target=peaks,
            mu=mu,
            options=cvx_options(**options),
            )
        s = get_variable(problem,'s').round(2)
        b = get_variable(problem,'b').round(2)
        # assert (s==1.0).all(), f"{mu=}: {s=} not all 1.0"
        # assert (b==0.0).all(), f"{mu=}: {b=} not all 0.0"
    print("ok")
