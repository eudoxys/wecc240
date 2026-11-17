# Models

- [x] **Milestone 1: WECC 240 (2011)** (see `wecc240.wecc240_2011`)

  The 2011 CAISO model of Price and Goodin, converted from the PSS/E RAW
  file by `wecc240/build_wecc240_2011.py`. Static (no time series); runs in
  `pypower` or `pypower_sim`. The pseudo-DC-line gen/load pairs are
  converted to explicit DC lines with costs.

- [x] **Milestone 2: WECC 240 (2018)** (see `wecc240.wecc240_2018`)

  NREL's 2018 update of the 2011 model: generator costs by type, branch
  ratings and voltage fixes, built by `wecc240/build_wecc240_2018.py`.
  Static; runs in `pypower` or `pypower_sim`.

- [ ] **Milestone 3: WECC 240 (2020)** (`wecc240.wecc240_2020`, in progress)

  Quasi-steady time-series model for `pypower_sim`, based on the 2018 model.
  Done: static case `wecc240_2020` at 1 January 2020 00:00 UTC, built by
  `wecc240/build_wecc240_2020.py` from `eudoxys/loads` node net loads and
  `eudoxys/generation` node generation by category. Remaining: hourly time
  series, voltages above 1.1 pu and overloaded branches in its power flow,
  decide where its time-series inputs live (#13), fix the aggregate scripts
  (#8, #9, #10).

- [ ] **Milestone 4: Energy storage**

  Storage scheduled for the CAISO "duck curve": charge 9am to 3pm,
  discharge 3pm to 9pm. The benefit shows only in a time-series simulation.

- [ ] **Milestone 5: Load curtailment**

  Three regimes:
  1. normal operation: no curtailment;
  2. node load within 10% of the node's line import capacity plus
     generation: "level 0", 10% of the node load curtailable;
  3. area load within 15% of the area's import capacity plus generation:
     "level 1", 15% of the area load curtailable.

- [ ] **Milestone 6: WECC 240 (2025)**

  The system as of Q3 2025 (LLNL, 2026): the 2020 model with new generation
  and new loads, including data centers.

# Eudoxys standards compliance

- [x] `CLAUDE.md`, `DESIGN.md` (draft), `MANIFEST.md`, `TODO.md` (this file)
- [x] Tests moved to `wecc240/_test/` (pytest) with a README
- [x] `.github/check_manifest.py`, run in CI
- [x] `validate.yaml` and `deploy-pages.yaml` per the templates (paths
      filters, concurrency, timeout, pip cache, non-editable install,
      sparse checkout without the data)
- [x] `__version__` from package metadata
- [x] Docs workflow builds again (Python 3.12, bash for `source`, pdoc
      skips the script modules until #11)
- [x] README and package docstring examples that run
- [ ] Working CLI in `wecc240/cli.py` (#5)
- [ ] Public API decided and re-exported from `__init__.py` (#12)
- [ ] Maintenance scripts moved to `_build/` / `_review/` (#11)
- [ ] Logging instead of `print` (#17)
- [ ] `requirements.txt` cleaned up (#15)
- [ ] Data READMEs with provenance (#14)
- [ ] Large data relocated or pruned (#13)
- [ ] Tests for the CLI, build scripts, private modules (#16)
- [ ] Generated `docs/` untracked (#18)
- [ ] Legacy `PSSE/` removed or fixed (#7)
- [ ] `DESIGN.md` open questions resolved and design agreed
- [ ] First release (`version` > `0.0.0`, tag `YEAR.MONTH.0`)
