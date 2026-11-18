"""Power flow and OPF tests on the static WECC 240 cases

Fast (seconds), self-contained: the cases are PYPOWER case files shipped
with the package, so no data is downloaded or read from `wecc240/data/`.
"""

import os

from pypower_sim import PPModel, PPSolver

from wecc240._case import Case

from wecc240.wecc240_2011 import wecc240_2011
from wecc240.wecc240_2018 import wecc240_2018
from wecc240.wecc240_2020 import wecc240_2020

def test_wecc240_2011_pf():
    """The 2011 case has no generator costs, so only the power flow applies"""
    model = PPModel(name="wecc240_2011",case=wecc240_2011)
    solver = PPSolver(model)
    assert solver.solve_pf(), "PF failed"

def test_wecc240_2018_opf_pf():
    """The 2018 case solves both OPF and power flow"""
    model = PPModel(name="wecc240_2018",case=wecc240_2018)
    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

def test_wecc240_2020_opf_pf():
    """The 2020 case (peak CAISO net load hour) solves both OPF and power flow
    with its HVDC lines (`_case.Case.solve`; `PPSolver` ignores `dcline`, and
    the 2020 dispatch needs the HVDC transfers)"""
    case = Case.load(os.path.join(os.path.dirname(__file__),"..","wecc240_2020.py"))
    assert case.solve("opf")["success"], "OPF failed"
    assert case.solve("pf")["success"], "PF failed"

def test_case_shapes():
    """All cases have 243 buses and the same network topology"""
    for case in (wecc240_2011(),wecc240_2018(),wecc240_2020()):
        assert case["bus"].shape[0] == 243
        assert case["baseMVA"] == 100
        assert case["branch"].shape == wecc240_2011()["branch"].shape
    assert wecc240_2011()["gen"].shape[0] == wecc240_2018()["gen"].shape[0]
    case = wecc240_2020()
    assert case["gen"].shape[0] >= wecc240_2018()["gen"].shape[0]
    assert case["gencost"].shape[0] == case["gen"].shape[0]
