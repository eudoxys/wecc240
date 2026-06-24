"""WECC 240 simulation

"""

import os
import sys
import numpy as np
import pandas as pd

import pypower_sim as ps
from pypower_sim.ppmodel import idx_bus as bus
from utilities import CommandLine

E_OK = 0 # no error return code

refresh = False # force refresh of intermediate files

def main(argv=sys.argv):
    """Main entry function

    Arguments
    ---------
    - *args: position arguments (from command line by default)
    - **kwargs: keyword arguments (from command line by default)

    Returns
    -------
    - int: return code

    Raises
    ------
    - Exception: uncaught exception
    """

    cmdline = CommandLine(argv,nocommand=True)

    model = ps.PPModel(cmdline.args[0],case=cmdline.args[0]+".py")

    # calculate reactive power load from real power load  
    if not os.path.exists("data/wecc240_bus_QD.csv.gz") or refresh:
        print("Generating reactive power load",end="...",flush=True)
        P = pd.read_csv("data/wecc240_bus_PD.csv.gz",index_col=[0],parse_dates=[0])
        busmap = {str(int(y)):x for x,y in enumerate(model.case["bus"][:,bus.BUS_I])}
        Q = []
        qfactor = model.case["bus"][:,bus.QD] / model.case["bus"][:,bus.PD]
        for column in P.columns:
            p = P[column].ffill().bfill()
            q = p * qfactor[busmap[column]]
            Q.append(pd.DataFrame(
                data={
                column: q,
                },
                index=P.index).ffill().bfill())
        Q = pd.concat(Q,axis=1)
        Q.to_csv("data/wecc240_loadQ.csv.gz",index=True,compression="gzip")
        print("ok",flush=True)

    datamgr = ps.PPData(model)
    datamgr.set_input(
        name="bus",
        column="PD",
        file="data/wecc240_bus_PD.csv.gz",
        mapping="BUS_I",
        scale=1/model.case["baseMVA"]
        )
    datamgr.set_input(
        name="bus",
        column="QD",
        file="data/wecc240_bus_QD.csv.gz",
        mapping="BUS_I",
        scale=1/model.case["baseMVA"]
        )
    datamgr.set_output(
        name="branch",
        column="PF",
        file="data/wecc240_branch_PF.csv",
        scale=model.case["baseMVA"]
        )
    datamgr.set_output(
        name="branch",
        column="QF",
        file="data/wecc240_branch_QF.csv",
        scale=model.case["baseMVA"]
        )
    datamgr.set_output(
        name="branch",
        column="PT",
        file="data/wecc240_branch_PT.csv",
        scale=model.case["baseMVA"]
        )
    datamgr.set_output(
        name="branch",
        column="QT",
        file="data/wecc240_branch_QT.csv",
        scale=model.case["baseMVA"]
        )

    solver = ps.PPSolver(model)
    oce = ps.OceOptions()
    errors = solver.run_timeseries(
        start="2020-08-01 07:00:00+0000",
        end="2020-08-08 06:00:00+0000",
        freq="1h",
        progress=lambda *x,**y:print(f"Processing {y['event']} {y['timestamp']} ({len(y['errors'])} errors so far)",flush=True),
        use_acopf=None,
        stop_on_fail=True,
        violations=True,
        )
    print(f"Done with {'no' if errors is None else len(errors)} errors")
    
    return E_OK


if __name__ == '__main__':
    
    sys.exit(main(["wecc240_2018"]))
