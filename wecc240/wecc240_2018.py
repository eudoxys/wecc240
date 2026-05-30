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

from numpy import array

from pypower_sim import PPModel, PPSolver


# pylint: disable=too-many-lines,invalid-name,line-too-long

def wecc240_2018():
    """WECC 240 model by Price et al."""

    from wecc240.wecc240_2011 import wecc240_2011
    from wecc240.scheduling import Generator
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
    # model.options["VERBOSE"] = 3
    # model.options["OUT_ALL"] = 1
    # model.options["OPF_ALG"] = 0
    # assert solver.solve_opf(use_acopf=True), "OPF failed"
    # assert solver.solve_pf(), "PF failed"

    import pandas as pd
    pd.options.display.max_columns = None
    pd.options.display.width = None
    pd.options.display.max_rows = None
    
    with open("case240_2018.py","w") as fh:
        model.save_case(fh,name="case240_2018")
