"""Download the EIA Form 930 hourly load of the WECC balancing authorities

Syntax: python3 form930_load.py [YEAR] [OUTPUT]

Writes `OUTPUT` (default `form930_load_{YEAR}.csv.gz` next to this script):
one row per UTC hour-beginning `timestamp` of `YEAR` (default 2020) and one
column per balancing authority in `RESPONDENTS`, the Form 930 demand
(`load_mw`, MW) read with `eia.Form930` (`eudoxys/eia`). Needs an EIA Open
Data API key (`~/.eia/api_key` or `EIA_API_KEY`) and network access to
eia.gov.

`build_wecc240_2020.py` uses the annual peak of each column to scale the
county loads of each balancing authority.
"""

import os
import sys

import pandas as pd
from eia import Form930

RESPONDENTS = ["AVA","AZPS","BANC","BPAT","CHPD","CISO","DOPD","EPE","GCPD","IID",
    "IPCO","LDWP","NEVP","NWMT","PACE","PACW","PGE","PNM","PSCO","PSEI","SCL","SRP",
    "TEPC","TIDC","TPWR","WACM","WALC","WAUW"]
"""US load-serving balancing authorities in WECC (EIA-860 plant BA codes
without generation-only and non-WECC authorities)"""

def main(year=2020,output=None):
    """Write the hourly Form 930 load of `RESPONDENTS` for a year"""
    output = output or os.path.join(os.path.dirname(os.path.abspath(__file__)),
        f"form930_load_{year}.csv.gz")
    data = {}
    for ba in RESPONDENTS:
        load = Form930(year,respondent=ba)["load_mw"]
        data[ba] = load[load.index.year == year]
        print(f"{ba}: {len(data[ba])} hours, peak {data[ba].max():.0f} MW at {data[ba].idxmax()}",flush=True)
    result = pd.DataFrame(data)
    result.index.name = "timestamp"
    result.round(1).to_csv(output)
    print(f"wrote {output}")

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2020,sys.argv[2] if len(sys.argv) > 2 else None)
