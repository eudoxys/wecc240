[![validate](https://github.com/eudoxys/wecc240/actions/workflows/validate.yaml/badge.svg)](https://github.com/eudoxys/wecc240/actions/workflows/validate.yaml)
[![Deploy Pages](https://github.com/eudoxys/wecc240/actions/workflows/deploy-pages.yaml/badge.svg)](https://github.com/eudoxys/wecc240/actions/workflows/deploy-pages.yaml)

WECC 240 bus models

`wecc240` provides reduced-network PYPOWER models of the Western
Electricity Coordinating Council (WECC) interconnection for power flow, OPF
and quasi-steady time-series studies with `pypower` and `pypower_sim`. The
static 2011 and 2018 cases are generated from the original PSS/E case and
NREL's 2018 generation update; the 2020 model (in progress) adds hourly
node loads, distributed generation, solar and wind built from county-level
load models (`eudoxys/loads`), EIA data, and Canadian and Mexican utility
data.

Note that "WECC 240" is a misnomer: the more recent models have 243 buses.

# Documentation

See https://www.eudoxys.com/wecc240

# Installation

Install using Eudoxys Package Manager:

    pip install --upgrade eudoxys
    epm install wecc240

Install using `pip`:

    pip install git+https://github.com/eudoxys/wecc240

The package requires Python 3.12.

# Maintenance

## Update docs

    make docs

## Run tests

    pip install -e . pytest
    pytest

The tests need no credentials or downloads; see
[`wecc240/_test/README.md`](wecc240/_test/README.md).

## Rebuild the cases

The PYPOWER case files are generated; don't edit them by hand.

    python3 wecc240/build_wecc240_2011.py
    python3 wecc240/build_wecc240_2018.py

See [`wecc240/README.md`](wecc240/README.md) for the data flow.

## Large data

The repository holds about 900 MB of time-series and source data under
`wecc240/data/`, `wecc240/Canada/` and `wecc240/wecc240_2020_*.csv`, which
the static cases and the tests don't need. Clone without it when you are
not changing the data:

    git clone --filter=blob:none --sparse https://github.com/eudoxys/wecc240

# Examples

## Python

Load the 2018 model and solve the optimal and AC power flow (the 2011 case
has no generator costs, so only its power flow can be solved):

    from wecc240.wecc240_2018 import wecc240_2018
    from pypower_sim import PPModel, PPSolver

    model = PPModel(name="wecc240_2018",case=wecc240_2018)
    solver = PPSolver(model)
    assert solver.solve_opf(), "OPF failed"
    assert solver.solve_pf(), "PF failed"

## Available models

- `wecc240.wecc240_2011`: the original model published by Price et al. [1],
  as converted to PYPOWER, with the HVDC lines as explicit DC lines.
- `wecc240.wecc240_2018`: the 2011 model with NREL's 2018 generator costs,
  branch ratings and voltage fixes.
- `wecc240.wecc240_2020`: quasi-steady time-series model (in progress; see
  [TODO.md](TODO.md)).

The roadmap is in [TODO.md](TODO.md).

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

# Acknowledgments

- This material is based on work supported by the U.S. Department of Energy’s Office of Electricity through a grant from the Grid Controls and Communications Division
