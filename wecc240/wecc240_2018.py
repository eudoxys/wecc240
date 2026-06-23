"""WECC 240 Model Version 2

The WECC 240 Model Version 2 is based on the model from the 2018 paper by Yuan et al [1].

# Example

    from wecc240_2011 import WECC240_2011
    from pypower_sim import PPModel, PPSolver

    model = WECC240_2011()
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

import numpy as np

from pypower_sim import PPModel, PPSolver, OceOptions
from pypower_sim.ppmodel import idx_gen as gen
from pypower_sim.ppmodel import idx_bus as bus
from pypower_sim.ppmodel import idx_branch as branch


# pylint: disable=too-many-lines,invalid-name,line-too-long

def wecc240_2018(adjustments:dict[tuple,float]|None=None) -> dict:
    """WECC 240 model by Price et al.

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
    from wecc240_2011 import wecc240_2011
    data = wecc240_2011()

    # read generator schedule update
    from scheduling import Generator
    gens = Generator()

    # apply generator schedule to base model
    data["gen"] = gens.to_ppgen()
    data["gencost]"] = gens.to_ppgencost()

    # apply specified adjustments
    for key,scalar in adjustments.items():
        data[key[0]][:,key[1]] *= scalar
    
    # fix bus types according to generator schedule
    busmap = {int(y):x for x,y in enumerate(data["bus"][:,bus.BUS_I])}
    genbus = [busmap[x] for x in data["gen"][:,gen.GEN_BUS]]
    refbus = [busmap[x] for x in data["bus"][data["bus"][:,bus.BUS_TYPE]==3][:,bus.BUS_I]]
    assert len(refbus) == 1, f"{len(refbus)} reference busses, only 1 reference bus is supported"
    data["bus"][:,bus.BUS_TYPE] = 1
    data["bus"][genbus,bus.BUS_TYPE] = 2
    data["bus"][refbus,bus.BUS_TYPE] = 3

    return data

class WECC240_2018(PPModel):
    """WECC240 version 1 (2011) model for `pypower_sim`"""

    def __init__(self,adjustments=None):
        """Construct WECC240 model version 1 (2011)"""

        super().__init__(name="wecc240_2018",case=wecc240_2018(adjustments))

if __name__ == "__main__":

    model = WECC240_2018(adjustments={
        # ("branch",branch.BR_B): 1/25, # reduce susceptance to make AC OPF solvable
        })
    
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
    
    with open("case240_2018.py","w") as fh:
        model.save_case(fh,name="case240_2018")
