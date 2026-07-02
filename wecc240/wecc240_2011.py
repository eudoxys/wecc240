"""WECC 240 Model Version 1

The WECC 240 Model Version 1 is based on the model from the 2011 paper by Price et al. [1].

# Example

    from wecc240_2011 import WECC240_2011
    from pypower_sim import PPModel, PPSolver

    model = WECC240_2011()
    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

# References

1. Price, James E., and John Goodin. "Reduced network modeling of WECC as a
market design prototype." In 2011 IEEE Power and Energy Society General
Meeting, pp. 1-6. IEEE, 2011.
"""

import sys
import numpy as np
from numpy import array, float64

from pypower_sim import PPModel, PPSolver
from pypower_sim.ppmodel import idx_bus as bus
from pypower_sim.ppmodel import idx_branch as branch

# pylint: disable=too-many-lines,invalid-name,line-too-long

def wecc240_2011():
    """WECC 240 model by Price et al."""
    _path = sys.path
    sys.path.append("PSSE")
    from wecc240_psse import wecc240_psse
    data = wecc240_psse()
    sys.path = _path

    # convert branch susceptances to puZ
    busmap = {int(y):x for x,y in enumerate(data["bus"][:,bus.BUS_I])}
    puZ = data["baseMVA"] / data["bus"][:,bus.BASE_KV]**2
    fbus = data["branch"][:,branch.F_BUS]
    data["branch"][:,branch.BR_B] *= np.array(puZ[[np.s_[busmap[x]] for x in fbus]])

    return data

class WECC240_2011(PPModel):
    """WECC240 version 1 (2011) model for `pypower_sim`"""

    def __init__(self):
        """Construct WECC240 model version 1 (2011)"""

        super().__init__(name="wecc240_2011",case=wecc240_2011)

if __name__ == "__main__":

    model = WECC240_2011()
    
    model.options["OUT_ALL"] = 1

    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

    with open("case240_2011.py","w") as fh:
        model.save_case(fh,name="case240_2011")
