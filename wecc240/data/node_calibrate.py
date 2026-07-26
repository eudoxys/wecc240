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

def _solver(X:np.array,
            E_target:float|list[tuple[list[int],float]]=None,
            P_target:float|list[tuple[list[int],float]]=None,
            *,
            gamma:float=1.0,
            mu:float=0.0,
            lam:float=0.0,
            eps:float=1e-3,
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

    Description
    -----------

    This solver scales and offsets the array X such that the total of the rows
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

    When multiple `E_target` or `P_target` objectives are sought, these can be
    specified as a list of columns with the target value, e.g.,

        [([1,2,3], 1.23),
         ([4,5,6], 4.56),
         ]

    Note that a column may appear in more than one target if desired.
    """
    
    T, n = X.shape

    a = cp.Constant(X.sum(axis=0),name='a')     # column energy weights, shape (n,)
    c = cp.Constant(X.min(axis=0),name='c')     # per-column minima (for output nonneg reduction)

    if E_target is None: E_target = np.sum(X)
    E = cp.Constant(E_target,name='E')          # total energy target scalar

    if P_target is None: P_target = np.max(np.sum(X,axis=1))
    P = cp.Constant(P_target,name='P')          # peak power target scalar

    s = cp.Variable(n, nonneg=True, name='s')   # per-column scaling factors
    b = cp.Variable(n, name='b')                # per-column offsets

    # Output signal: column j is s_j * X[:,j] + b_j (broadcast over rows)
    Y = cp.multiply(X, cp.reshape(s, (1, n))) + cp.reshape(b, (1, n))

    peak = cp.max(cp.sum(Y, axis=1))            # max row-sum of OUTPUT (convex)
    energy = cp.sum(Y)                          # total energy of OUTPUT (affine)

    mu = cp.Constant(mu,name='mu')
    lam = cp.Constant(lam,name='lam')
    gamma = cp.Constant(gamma,name='gamma')
    eps = cp.Constant(eps,name='eps')

    objective = cp.Minimize(
        gamma * cp.sum_squares(Y - X) / T**2           # == ||X diag(s) + 1 b^T - X||_F^2
        + mu * cp.square(energy - E) / T**2
        - lam * cp.sum(b) / n
        + eps * (cp.sum_squares(s - 1) + cp.sum_squares(b))
    )
    constraints = [
        peak <= P,                              # power inequality (convex relaxation)
        cp.multiply(s, c) + b >= 0,             # output nonnegativity (reduced form)
                                                # equivalent full form: Y >= 0
    ]

    prob = cp.Problem(objective, constraints)
    assert prob.is_dcp(), "ERROR: problem is not DCP"
    result = prob.solve(**options)

    if prob.status not in ("infeasible", "unbounded"):
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
        print("Problem status:", prob.status)

    return result,prob