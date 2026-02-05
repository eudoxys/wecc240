"""Compile BC Hydro data into c2c10y.csv file


The tieline data has been manually processed to remove erroneous extra rows of
zeros when summer time begins and convert the file to CSV format. Note that
hours are hour ending in local time.

References
----------

  - Tieline data from https://www.bchydro.com/energy-in-bc/operations/transmission/transmission-system/actual-flow-data/historical-data.html

  - Load data from https://www.bchydro.com/energy-in-bc/operations/transmission/transmission-system/balancing-authority-load-data/historical-transmission-data.html
"""

if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    losses = 0.067 # per BC Hydro loss calculator (https://www.bchydro.com/energy-in-bc/operations/transmission/transmission-scheduling/tariff-pricing/losses.html)

    dt_index = pd.date_range(
        start="2018-01-01 00:00:00-0800",
        end="2022-12-31 23:59:59-0800",
        freq="1h",
        ).tz_convert("UTC")

    # read tieline exports (energy from BC is positive)
    exports = -pd.read_csv("BCHydro/imports.csv",usecols=["US","AB"])
    exports.index = dt_index


    # read net loads
    loads = pd.read_csv("BCHydro/loads.csv",usecols=["elec_net_MW"])
    loads.index = dt_index

    # losses (only exports have losses that local generation supports)
    # loss = (loads["elec_net_MW"] + exports.sum(axis=1).clip(lower=0).to_frame()[0]) * losses

    # local generation
    # gen = loads["elec_net_MW"] + exports.sum(axis=1).to_frame()[0] + loss

    c2c10y = pd.DataFrame(
        data={
            "dispatch_MW": loads.elec_net_MW + exports.US + exports.AB,
            "capacity_MW": 12049.0 + 5500.0, # BCHydro + IPP
            "load_MW": loads.elec_net_MW,
        },
        index = dt_index,
        ).round(3)
    c2c10y.index.name = "timestamp"

    c2c10y.to_csv("c2c10y.csv",header=True,index=True)
