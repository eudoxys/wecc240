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

from numpy import array

from pypower_sim import PPModel, PPSolver


# pylint: disable=too-many-lines,invalid-name,line-too-long

def wecc240_2018():
    """WECC 240 model by Price et al."""

    from wecc240_2011 import wecc240_2011
    from scheduling import Generator
    data = wecc240_2011()
    gens = Generator()
    data["gen"] = gens.to_ppgen()
    data["gencost]"] = gens.to_ppgencost()

    return data

class WECC240_2018(PPModel):
    """WECC240 version 1 (2011) model for `pypower_sim`"""

    def __init__(self):
        """Construct WECC240 model version 1 (2011)"""

        super().__init__(name="wecc240_2018",case=wecc240_2018)

if __name__ == "__main__":

    model = WECC240_2018()
    
    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

    import pandas as pd
    pd.options.display.max_columns = None
    pd.options.display.width = None
    pd.options.display.max_rows = None
    
    model.print()
