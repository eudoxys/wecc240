"""Package-level contracts: version and installed data files

Fast, self-contained. Run from a non-editable install (`pip install .`) these
also catch package data missing from `[tool.setuptools.package-data]`.
"""

import os

import wecc240

def test_version():
    """`__version__` is read from the installed metadata"""
    assert isinstance(wecc240.__version__,str) and wecc240.__version__

def test_package_data():
    """The curated files the build scripts read are installed"""
    here = os.path.dirname(wecc240.__file__)
    for name in ("wecc240_bus.csv","wecc240_cost.csv","wecc240_gentypes.csv",
            "wecc240_geodata.csv","wecc240_case.raw"):
        assert os.path.exists(os.path.join(here,name)), f"{name} not installed"
