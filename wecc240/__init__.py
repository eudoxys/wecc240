"""WECC 240 models

[![validate](https://github.com/eudoxys/wecc240/actions/workflows/validate.yaml/badge.svg)](https://github.com/eudoxys/wecc240/actions/workflows/validate.yaml)

# Documentation

See https://www.eudoxys.com/wecc240 for online documentation.

# Available models

The following models are available

- `wecc240.wecc240_2011.WECC240_2011`: the original model published by
  Price et al. [1].

# Example

The following python code loads and solve the original WECC 240 model from Price et al. [1].

    from wecc240_2011 import WECC240_2011
    from pypower_sim import PPModel, PPSolver
    
    model = WECC240_2011()
    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

# References

1. J. E. Price and J. Goodin, "Reduced network modeling of WECC as a market
design prototype," 2011 IEEE Power and Energy Society General Meeting,
Detroit, MI, USA, 2011, pp. 1-6, doi: 10.1109/PES.2011.6039476. URL:
https://ieeexplore.ieee.org/abstract/document/6039476.
"""

from .wecc240_2011 import WECC240_2011
