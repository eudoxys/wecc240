"""Build wecc240/wecc240_2011.py: the 2011 WECC 240 case from the PSS/E RAW file

Syntax: python3 wecc240/build_wecc240_2011.py

Converts `wecc240/wecc240_case.raw` (the 2011 WECC 240-bus case, PSS/E
revision 34) to `wecc240/wecc240_case.py` (case name `wecc240_case`, no
geodata). Then reads that file back, adds the bus locations in
`wecc240/wecc240_geodata.csv`, and writes `wecc240/wecc240_2011.py` (case
name `wecc240_2011`).

The PSS/E case models the two HVDC lines in `DCLINES` as a load at the
rectifier bus and a negative load at the inverter bus. Each becomes a
PYPOWER `dcline` row that takes the rectifier load as `Pf` with losses of
`LOSS1` (3.5%) of `Pf`, so `Pt = Pf * (1 - LOSS1)`. The rectifier bus load
is set to 0 and `Pt` is added to the inverter bus load; what is left there
is load at the inverter bus, so the power flow solution is unchanged.
`Pmin` is 0 and `Pmax` is `Pf`, there is no reactive power, and `Vf`, `Vt`
are the case voltages (`Vm`) of the terminal buses. The DC lines have zero
polynomial `dclinecost`.

Uses `_case.py`, `_psse.py` and `_dcline.py`, copied from
https://github.com/dchassin/ppedit; ppedit itself is not needed.
"""

import os

from _case import Case # pylint: disable=import-error

HERE = os.path.dirname(os.path.abspath(__file__))

DCLINES = [(4010,2619),(2604,2600)]
"""HVDC lines as (rectifier bus, inverter bus): the Pacific DC Intertie
(CELILO to SYLMARLA) and the Intermountain line (INTERMT to ADELANTO)"""

LOSS1 = 0.035
"""DC line losses as a fraction of `Pf` (`loss1`)"""

def main():
    """Write wecc240/wecc240_case.py and wecc240/wecc240_2011.py"""
    case = Case.load(os.path.join(HERE,"wecc240_case.raw"))
    case.name = "wecc240_case"
    case.save(os.path.join(HERE,"wecc240_case.py"))
    print(f"wrote wecc240/wecc240_case.py: {case.size()}")
    case = Case.load(os.path.join(HERE,"wecc240_case.py"))
    case.load_geodata(os.path.join(HERE,"wecc240_geodata.csv"))
    buses = {row[0]:row for row in case.tables["bus"]}
    for fbus,tbus in DCLINES:
        rectifier,inverter = buses[fbus],buses[tbus]
        if rectifier[2] <= 0 or inverter[2] >= 0:
            raise ValueError(f"DC line {fbus}-{tbus} is not a load at {fbus} "
                f"and a negative load at {tbus}")
        if rectifier[3] != 0 or inverter[3] != 0:
            raise ValueError(f"DC line {fbus}-{tbus} terminal buses have reactive load")
        pf = rectifier[2]
        pt = pf * (1 - LOSS1)
        case.add_row("dcline",{"fbus":fbus,"tbus":tbus,"status":1,"Pf":pf,"Pt":pt,
            "Vf":rectifier[7],"Vt":inverter[7],"Pmin":0.0,"Pmax":pf,"loss1":LOSS1})
        rectifier[2] = 0.0
        inverter[2] += pt
    case.tables["dclinecost"] = [[2,0.0,0.0,3,"0,0,0"] for _ in case.tables["dcline"]]
    case.name = "wecc240_2011"
    errors = [x["message"] for x in case.validate() if x["level"] == "error"]
    if errors:
        raise ValueError("; ".join(errors))
    case.save(os.path.join(HERE,"wecc240_2011.py"))
    print(f"wrote wecc240/wecc240_2011.py: {case.size()}")

if __name__ == "__main__":
    main()
