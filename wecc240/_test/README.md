Testing
-------

From the repository root:

	python3.12 -m venv .venv
	. .venv/bin/activate
	python3 -m pip install --upgrade pip
	pip install -e . pytest
	pytest

No credentials are needed and nothing is downloaded. The full suite runs in
a few seconds. CI installs with `pip install .` (non-editable) so missing
package data is caught.

Environment variables:

  - `WECC240_CACHEDIR`: cache folder for sibling packages that use the
    Eudoxys `cache` package (default: the `cache` package default)

`test_cases.py`
---------------

Solves the static PYPOWER cases shipped with the package: power flow on
`wecc240_2011` (it has no generator costs) and OPF plus power flow on
`wecc240_2018`, and checks their shapes (243 buses, same branches and
generators). Fast: the cases are checked in, so no data is read or
downloaded. Run alone:

	pytest wecc240/_test/test_cases.py

`test_package.py`
-----------------

Checks `wecc240.__version__` and that the curated CSV and RAW files read by
the build scripts are installed with the package. Run alone:

	pytest wecc240/_test/test_package.py

Not yet tested
--------------

`wecc240_2020`, the `wecc240` CLI, the `aggregate_*` scripts and the build
scripts have no tests yet; see `TODO.md` and the open issues.
