# CLAUDE.md

Repository notes for automated coding tools (Claude Code and similar)
used in the `eudoxys/wecc240` repository. General Eudoxys package
conventions are in the `eudoxys-package` skill
(https://github.com/eudoxys/claude); this file records only what is
specific to this package.

## What this is

Reduced-network (243-bus) PYPOWER models of the WECC interconnection. The
static 2011 and 2018 cases are generated PYPOWER case files built from the
2011 PSS/E RAW case and NREL's 2018 generation scheduling data; the static
2020 case is the 2018 network at the 2020 peak CAISO net load hour with node
loads from `eudoxys/loads` scaled to Form 930 balancing authority peaks,
node capacity and output from `eudoxys/generation`, and an OPF dispatch. Hourly 2020
time series are in progress. Python 3.12, alpha, unreleased (`version = "0.0.0"`).

- Docs site: https://www.eudoxys.com/wecc240 (pdoc from docstrings)
- Maintainer: David P. Chassin (`dchassin`)
- CLI entry point: `wecc240` -> `wecc240.wecc240:main` (broken when
  installed; #5)

## Where things are

- `MANIFEST.md`: map of every file, a task index, and what not to read.
  Read it first instead of listing folders.
- `DESIGN.md`: draft design, numbered decisions, planned work and open
  questions. Follow its decisions; ask before departing from one.
- `wecc240/README.md`: case files, build scripts and their data flow.

Sibling Eudoxys dependencies:
- `pypower_sim`: `PPModel`, `PPSolver`, `PPData` (solving and time series)
- `pypower` (eudoxys fork): the solver, `idx_*` column indexes
- `loads`: county-level load models (`loads.aggregate`) for the 2020 model
- `utilities`: `CommandLine` (current CLI)
- `eia`, `fips`, `geohash`: used only by scripts under `wecc240/data/`

## Core conventions

- Case files (`wecc240_2011.py`, `wecc240_2018.py`, `wecc240_2020.py`,
  `wecc240_case.py`, `wecc240_map.py`) are **generated**; change the build scripts or their
  CSV inputs and rebuild, never edit them by hand.
- Each case module defines a function of the same name returning the
  PYPOWER case dict (except `wecc240_map.py`, whose function is
  `wecc240_case`; #11).
- PSS/E constant-admittance load `YQ > 0` is capacitive: it **reduces**
  `QD` (`_psse.py`, as MATPOWER `psse2mpc`). The legacy `PSSE/raw2py.py`
  gets this wrong (#7); don't copy from it.
- Network nodes in the time-series data are identified by 6-character
  geohash (e.g. `9qeh90`), mapped to buses in `wecc240/gis/wecc240.csv`.
- Time series use UTC indexes; Canadian and Mexican nodes (`c2c10y`,
  `c2u6xt`, `9mtzm4`) are built from utility data by the scripts in
  `wecc240/Canada/` and `wecc240/Mexico/`.
- Units are MW / MVAr in data files and per-unit on `baseMVA = 100` inside
  cases (`PPData` inputs scale by `1/baseMVA`).

## Style

Compact house style: no spaces after commas in calls and signatures,
4-space indents, `"""` docstrings with dashed-underline sections. Match it;
don't reformat code you aren't changing.

## Build, test, docs

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install --upgrade pip && pip install -e . pytest
pytest                                  # seconds; no downloads
make docs                               # pdoc into docs/
python3 .github/check_manifest.py       # MANIFEST.md covers git ls-files
python3 wecc240/build_wecc240_2011.py   # regenerate the 2011 case
python3 wecc240/build_wecc240_2018.py   # regenerate the 2018 case
python3 wecc240/build_wecc240_2020.py --raise-ratings   # regenerate the 2020 case (reads loads/generation data)
```

CI (`validate.yaml`) installs non-editable, runs the manifest check,
pylint (informational) and pytest, with a sparse checkout that omits the
large data.

## Known rough edges (don't "fix" silently; mention or ask)

- The `wecc240` CLI fails when installed (#5).
- `build_wecc240_2020.py --raise-ratings` raises `rateA` on the branches
  its dispatch loads above the 2018 rating (23 at the default hour),
  because the OPF is infeasible with the 2018 ratings; the ratings need
  review. The county-to-balancing-authority split from EIA-860 plants gives
  extreme factors for small authorities (GCPD ×18, DOPD ×5, WAUW ×0.35).
- `pypower_sim.PPSolver` ignores the `dcline` table; the 2020 case's OPF
  needs its HVDC lines, so its test solves with `_case.Case.solve`.
- `wecc240.WECC240_2011` / `WECC240_2018` are case dicts built at import
  time, not classes (#12).
- `aggregate_*.py` and `viewer.py` disagree on 2020 vs 2025 file names, and
  some read from `~/Downloads` (#8, #9, #10); `aggregate_gens.py` runs on
  import (#11).
- `PSSE/raw2py.py` inverts the `YQ` sign (#7).
- ~900 MB of data is tracked; most is not shipped or tested (#13).
- `docs/` is committed but stale (#18).

## Working rules

- Clone with `--filter=blob:none --sparse` (or sparse-checkout) unless the
  task changes the data. When committing from a sparse checkout, check
  `git status` shows no unintended deletions before pushing.
- Don't commit caches, downloads, marimo session folders, or CLI outputs.
  Curated data changes need the producing script and an updated data
  README.
- When a public signature, case content or output changes: update the
  module docstring, `wecc240/__init__.py`, `README.md` and `DESIGN.md` in
  the same PR.
- Update `MANIFEST.md` when adding, moving, or deleting files, and run
  `.github/check_manifest.py`.
- Conventional small test case: `wecc240_2018` (OPF + PF, about a second).
  Don't run the aggregate scripts or full-year time series unprompted;
  they need large inputs and take a long time.
- New issues: label `approved` and a `priority: high|medium|low` label,
  set the issue type (Bug, Task, Feature), assign `dchassin`.
