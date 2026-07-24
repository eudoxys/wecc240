# Setup and solve the problem
# Set the default cvxpy solve options
import numpy as np
import cvxpy as cp

def cvx_options(**kwargs):
    """Specify default cvx problem options
    
    Arguments
    ---------
    - `**kwargs`: modifications to default to appy to this option set"""
    options = {
        "solver": "clarabel",
        "verbose": True,
    }
    options.update(kwargs)
    return options

def _solver(X:np.array,
               E_target:float=None,
               P_target:float=None,
               *,
               gamma:float=1.0,
               mu:float=0.0,
               lam:float=0.0,
               eps:float=1e-3,
               options:dict=cvx_options(),
              ):
    """Solve the single energy/power target using scale only

    Arguments
    ---------
    - `X(T, n)`: nonnegative array of time-series signals
    - `E_target`: scalar energy target
    - `P_target`: scalar power target
    - `gamma`: shape fidelity (anti-crushing) -- primary regularizer
    - `mu`: energy target objective hyperparameter (recovers energy equality)   
    - `lam`: power target objective hyperparameter (presses peak to ceiling)
    - `eps`: small symmetric redice guaranteed a unique solution when zero or constant columns are present
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
        gamma * cp.sum_squares(Y - X)           # == ||X diag(s) + 1 b^T - X||_F^2
        + mu * cp.square(energy - E)
        - lam * cp.sum(b)
        + eps * (cp.sum_squares(s - 1) + cp.sum_squares(b))
    )
    constraints = [
        peak <= P,                              # power inequality (convex relaxation)
        cp.multiply(s, c) + b >= 0,       # output nonnegativity (reduced form)
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