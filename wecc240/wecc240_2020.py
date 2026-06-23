"""WECC 240 Model Version 3

The WECC 240 Model Version 3 is based on the model from the 2018 paper by Yuan
et al [1] with DG and dynamic loads added.

# Example

    from wecc240_2020 import WECC240_2020
    from pypower_sim import PPModel, PPSolver

    model = WECC240_2020()
    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

# References

1. [https://ieeexplore.ieee.org/document/9299666](H. Yuan, R. S. Biswas, J.
Tan and Y. Zhang, "Developing a Reduced 240-Bus WECC Dynamic Model for
Frequency Response Study of High Renewable Integration," 2020 IEEE/PES
Transmission and Distribution Conference and Exposition (T&D), Chicago, IL,
USA, 2020, pp. 1-5, doi: 10.1109/TD39804.2020.9299666.)
"""

import warnings

import numpy as np
import pandas as pd

from pypower_sim import PPModel, PPSolver, PPData
from pypower_sim.ppmodel import idx_gen as gen
from pypower_sim.ppmodel import idx_bus as bus
from pypower_sim.ppmodel import idx_branch as branch


# pylint: disable=too-many-lines,invalid-name,line-too-long

def wecc240_2020(adjustments:dict[tuple,float]|None=None) -> dict:
    """WECC 240 model by Chassin et al.

    Arguments
    ---------

    - `adjustments`: specifies the scalars to apply to columns of the case data

    Description
    -----------

    An adjustment is specified in the form `{(TABLE,COLUMN): SCALAR}`, where
    `TABLE` specifies the case table, e.g., `bus`, `branch`, `gen`,
    `gencost`, `dcline`, or `dclinecost`, and `COLUMN` is taken from the
    corresponding index, e.g., `idx_bus`, etc.  The `SCALAR` is floating
    point value which scales the values in the specific `TABLE.COLUMN`
    """

    # read base wecc model
    from wecc240_2018 import wecc240_2018
    data = wecc240_2018()

    # read net load and set model to peak hour
    busmap = {str(int(y)):x for x,y in enumerate(data["bus"][:,bus.BUS_I])}
    P = pd.read_csv("data/wecc240_load.csv.gz",index_col=[0],parse_dates=[0]) / data["baseMVA"]
    total = P.sum(axis=1)
    peak = P[total==total.max()].index
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        qf = np.nan_to_num(data["bus"][:,bus.QD] / data["bus"][:,bus.PD],0).round(4)
    busndx = [busmap[x] for x in P.columns]
    data["bus"][busndx,bus.PD] = P.loc[peak]
    data["bus"][busndx,bus.QD] = P.loc[peak] * qf[busndx]

    # apply specified adjustments
    if not adjustments is None:
        assert isinstance(adjustment,dict), f"{adjustments=} must be a dict type"
        for key,scalar in adjustments.items():
            data[key[0]][:,key[1]] *= scalar

    return data

class WECC240_2020(PPModel):
    """WECC240 version 3 (2020) model for `pypower_sim`"""

    def __init__(self,adjustments=None):
        """Construct WECC240 model version 3 (2020)"""

        super().__init__(name="wecc240_2018",case=wecc240_2020(adjustments))

if __name__ == "__main__":

    model = WECC240_2020()

    data = PPData(model)
    
    solver = PPSolver(model)

    model.options["OUT_ALL"] = 1

    # ok,solution = solver.solve_oce(with_result=True)
    # assert ok, "OCE failed"
    # print("","Warnings","--------",*solution["warnings"],sep="\n")
    # print("","Updates","-------",*solution["updates"],sep="\n")


    assert solver.solve_opf(use_acopf=True), "AC OPF failed"
    assert solver.solve_pf(), "PF failed"
    violations = model.get_violations()
    if violations:
        print("VIOLATIONS","---------"," ","\n  ".join(violations))
    else:
        print("No violations")

    import pandas as pd
    pd.options.display.max_columns = None
    pd.options.display.width = None
    pd.options.display.max_rows = None
    
    with open("case240_2020.py","w") as fh:
        model.save_case(fh,name="case240_2020")
