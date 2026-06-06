## Load calibration procedure
```mermaid
flowchart LR

    form861m[EIA Form 861m] --> state_mwh.py
    form923[EIA Form 923] --> state_mwh.py
    hs861m[EIA HS 861m] --> state_mwh.py
    state_mwh.py --> state_mwh.csv

    node_dg.csv.gz --> dg_disaggregation.py
    ../gis/wecc240.csv --> dg_disaggregation.py
    dg_disaggregation.py --> bus_dg.csv.gz
```