"""WECC 240 models

# Available models

The following PYPOWER cases are available. Each module defines a function
of the same name that returns the PYPOWER case `dict`.

- `wecc240.wecc240_2011.wecc240_2011`: the original model published by
  Price et al. [1], with the HVDC lines as explicit `dcline` rows.

- `wecc240.wecc240_2018.wecc240_2018`: the 2011 model with generator costs
  by type, branch ratings and voltage fixes (NREL 2018 update).

`wecc240.WECC240_2011` and `wecc240.WECC240_2018` are those case dicts,
evaluated when the package is imported.

# Installation

Install using Eudoxys Package Manager:

    pip install --upgrade eudoxys
    epm install wecc240

Install using `pip`:

    pip install git+https://github.com/eudoxys/wecc240

# Example

The following python code loads the 2018 WECC 240 model and solves the
optimal and the AC power flow (the 2011 case has no generator costs, so
only its power flow can be solved).

    from wecc240.wecc240_2018 import wecc240_2018
    from pypower_sim import PPModel, PPSolver

    model = PPModel(name="wecc240_2018",case=wecc240_2018)
    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

# References

1. J. E. Price and J. Goodin, "Reduced network modeling of WECC as a market
design prototype," 2011 IEEE Power and Energy Society General Meeting,
Detroit, MI, USA, 2011, pp. 1-6, doi: 10.1109/PES.2011.6039476. URL:
https://ieeexplore.ieee.org/abstract/document/6039476.

2. H. Yuan, R. S. Biswas, J. Tan and Y. Zhang, "Developing a Reduced 240-Bus
WECC Dynamic Model for Frequency Response Study of High Renewable
Integration," 2020 IEEE/PES Transmission and Distribution Conference and
Exposition (T&D), Chicago, IL, USA, 2020, pp. 1-5, doi:
10.1109/TD39804.2020.9299666. URL:
https://ieeexplore.ieee.org/abstract/document/9299666.

# Package information

- Source code: https://github.com/eudoxys/wecc240

- Documentation: https://www.eudoxys.com/wecc240

- Issues: https://github.com/eudoxys/wecc240/issues

- License: https://github.com/eudoxys/wecc240/blob/main/LICENSE

- Dependencies:

    - see `requirements.txt`; the cases need only
      [numpy](https://pypi.org/project/numpy/) and are solved with
      [pypower_sim](https://github.com/eudoxys/pypower_sim)

----
"""

try:
    import importlib.metadata
    __version__ = importlib.metadata.version("wecc240")
except Exception: # pylint: disable=broad-exception-caught
    __version__ = "dev"

from .wecc240_2011 import wecc240_2011
WECC240_2011 = wecc240_2011()
from .wecc240_2018 import wecc240_2018
WECC240_2018 = wecc240_2018()
