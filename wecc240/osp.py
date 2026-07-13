"""Optimal sizing and placement of capacitors and condensers

"""

import sys

import cvxpy as cvx

from pypower_sim import PPSolver



if __name__ == "__main__":

    from wecc240_2011 import WECC240_2011 as WECC240

    model = WECC240()
    solver = PPSolver(model)

    print(f"{solver.solve_pf()=}")
    print(f"{solver.solve_opf()=}")

