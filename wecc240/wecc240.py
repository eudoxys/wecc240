"""WECC 240 simulation

"""

import os
import sys
import numpy as np
import pandas as pd

import pypower_sim as ps
from utilities import CommandLine

E_OK = 0 # no error return code

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
    if not os.path.exists("data/wecc240_loadQ.csv.gz"):
        def QfromP(P,pf_onpeak,pf_offpeak=1.0):
            """Estimate reactive power based on real power and a linear power factor function"""
            Pnorm = P/np.max(P)
            pf = Pnorm*(pf_onpeak-pf_offpeak)+pf_offpeak
            S = Pnorm / pf
            Q = np.sqrt(S**2 - Pnorm**2)
            return Q
        P = pd.read_csv("data/wecc240_load.csv.gz",index_col=[0],parse_dates=[0])
        Q = []
        for column in P.columns:
            p = P[column].ffill().bfill()
            q = QfromP(p,0.97)
            Q.append(pd.DataFrame(
                data={
                column: q,
                },
                index=P.index))
        pd.concat(Q,axis=1).to_csv("data/wecc240_loadQ.csv.gz",index=True,compression="gzip")

    datamgr = ps.PPData(model)
    datamgr.set_input(
        name="bus",
        column="PD",
        file="data/wecc240_load.csv.gz",
        mapping="BUS_I",
        )
    datamgr.set_input(
        name="bus",
        column="QD",
        file="data/wecc240_loadQ.csv.gz",
        mapping="BUS_I",
        )

    solver = ps.PPSolver(model)
    oce = ps.OceOptions()
    errors = solver.run_timeseries(
        start="2020-08-01 07:00:00+0000",
        end="2020-08-31 06:00:00+0000",
        freq="1h",
        progress=lambda *x,**y:print(f"Processing {y['event']} {y['timestamp']} ({len(y['errors'])} errors so far)",flush=True),
        use_acopf=None,
        with_oce=oce,
        stop_on_fail=False,
        )
    print(f"Done with {len(errors)} errors")

    
    return E_OK


if __name__ == '__main__':
    
    sys.exit(main(["wecc240_2011"]))
