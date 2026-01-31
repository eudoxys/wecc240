"""Compile AESO data into c2u6xt.csv file

Load and generation data for Alberta is applied to the c2u6xt node in the WECC model.

Notes
------

  - The AESO data from 2017 to 2020 and 2020 to 2023 do not match on May 1
    2020. The difference between the two is added to the 2020-2023 data in
    order to eliminate the discrepancy. This seems to be supported by the
    plot on Page 8 of the 2020 Annual Market Statistic, which are very
    similar to the monthly average load obtained after this correction.

References
----------

  - Load data from https://www.aeso.ca/market/market-and-system-reporting/data-requests/hourly-load-by-area-and-region/

  - Generation data from https://www.aeso.ca/market/market-and-system-reporting/data-requests/historical-generation-data/

  - 2020 Annual Market Statistic https://www.aeso.ca/download/listedfiles/2020-Annual-Market-Stats-FINAL.pdf
"""

if __name__ == "__main__":
    import os
    import pandas as pd

    pd.options.display.width = None
    pd.options.display.max_columns = None

    # process generation
    gens = []
    for file in sorted([x for x in os.listdir("AESO") if x.startswith("CSD") and x.endswith(".csv.gz")]):
        print("Reading",file,end="...",flush=True)
        data = pd.read_csv(f"AESO/{file}",
            index_col="Date (MST)",
            parse_dates=["Date (MST)"],
            usecols=["Date (MST)","Maximum Capability","Volume"]
            ).sort_index().groupby("Date (MST)").sum().round(3)
        data.rename({"Maximum Capability":"capacity_MW","Volume":"dispatch_MW"},inplace=True,axis=1)
        data.index = data.index.tz_localize(-7*3600).tz_convert("UTC")
        data.index.name = "timestamp"
        gens.append(data)
        print("ok")

    gens = pd.concat(gens)

    # process loads
    print("Reading 2017-2020 loads",end="...",flush=True)
    data = pd.read_excel("AESO/Hourly-load-by-area-and-region-2017-2020.xlsx",sheet_name=1).set_index(["DATE","HOUR ENDING"])[["SOUTH","NORTHWEST","NORTHEAST","EDMONTON","CALGARY","CENTRAL"]].sum(axis=1).to_frame().reset_index(drop=True)
    dt_index = pd.date_range(start="2017-01-01 07:00:00+0000",end="2020-05-01 05:00:00+0000",freq="1h")
    data.index = dt_index
    data.drop(pd.date_range(
        start="2017-01-01 07:00:00+0000",
        end="2018-01-01 06:00:00+0000",
        freq="1h"),inplace=True)
    loads = [data.iloc[:-1]]
    print("ok")
    
    print("Reading 2020-2023 loads",end="...",flush=True)
    data = pd.read_excel("AESO/Hourly-load-by-area-and-region-May-2020-to-Oct-2023.xlsx",sheet_name=0).set_index(["DT_MST"])[["Calgary","Central","Edmonton","Northeast","Northwest","South"]].sum(axis=1).to_frame().reset_index(drop=True)
    dt_index = pd.date_range(start="2020-05-01 05:00:00+0000",end="2023-11-01 04:00:00+0000",freq="1h")
    data.index = dt_index
    loads.append(data)
    print("ok")

    # fix step change
    last = loads[0].iloc[-1].values[0]
    first = loads[1].iloc[0].values[0]
    print(f"Adjusting AESO 2020-2023 loads by {(last-first)/1e3:.1f} GW")
    loads[1] = loads[1] + last - first

    # compile final loads
    loads = pd.concat(loads).round(3)
    loads.columns = ["load_MW"]
    loads.index.name="timestamp"

    print("Saving results",end="...",flush=True)
    result = pd.merge(gens,loads,left_index=True,right_index=True).sort_index()
    # print(result[result.index.drop_duplicated(keep=False)])
    result.to_csv("c2u6xt.csv",index=True,header=True)
    print("ok")
