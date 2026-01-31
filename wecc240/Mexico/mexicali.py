"""Compile Mexicali data into 9mtzm4.csv

Notes
-----

- No hourly data is available for Mexicali. Static values from the 2011 model are used.
"""

if __name__ == "__main__":
    import pandas as pd

    dt_index = pd.date_range(start="2018-01-01 08:00:00+0000",end="2023-01-01 07:00:00+0000",freq="1h")
    data = pd.DataFrame(
        {
            "dispatch_MW":[283.9]*len(dt_index),
            "capacity_MW":[700.0]*len(dt_index),
            "load_MW":[220.719]*len(dt_index),
        },
        index=dt_index,
        )
    data.index.name = "timestamp"
    data.to_csv("9mtzm4.csv")
