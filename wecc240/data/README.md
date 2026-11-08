## WECC 240 model data flow
```mermaid
flowchart TD
    
    Eudoxys --> fips.Counties
    fips.Counties -->|WECC| counties 
    
    states -->|index| state_mwh
    Eudoxys --> eia.Form923 ---->|gen| state_mwh
    Eudoxys --> eia.HS861m ---->|load| state_mwh
    Eudoxys --> eia.Form861m ---->|dg| state_mwh
    
    NLR --> solar_dg["aggregated_solar_dg"] ------->|rename
    columns| node_dg
    
    
    NLR --> gis.wecc240
    gis.wecc240 --> bus_gis
    bus_gis -->|LOAD>0 & FIPS!=""| bustype_load_US

    Eudoxys --> loads.Total
    loads.Total --->|elec_total_mw| county_total

    counties -->|county_st| county_node_map
    counties -->|ST.unique| states
    counties -->|columns| county_total
    bustype_load_US -->|geohash| county_node_map

    county_node_map -->|county_st,geohash| node_total 
    county_total --->|groupby.geohash.sum| node_total

    node_total -->|1/| mul1
    mul1 --> county_node_cf
    county_total --> mul1

    node_dg --> mul2
    county_node_cf --> mul2
    mul2 --> county_dg

    node_total --> sum1
    node_dg -->|-| sum1
    sum1 --> node_net

    county_total --> sum2
    county_dg -->|-| sum2
    sum2 --> county_net

    county_total -->|Σ
    states| state_total
    county_dg -->|Σ
        states| state_dg
    
    state_dg -->|-| sum3
    state_total --> sum3
    sum3 --> state_net

    state_mwh --> mul3
    state_net -->|1/Σ
        states| mul3
    mul3 --> state_scalar

    subgraph data/wecc240_data.py
        counties
        states
        bus_gis
        bustype_load_US

        node_dg
        node_total
        node_net

        county_node_cf
        county_node_map
        county_dg
        county_total
        county_net

        state_mwh
        state_total
        state_dg
        state_net
        state_scalar

        sum1((+))
        sum2((+))
        sum3((+))

        mul1((x))
        mul2((x))
        mul3((x))
    end
```

## EIA-930 balancing authority load disaggregation

The node loads in `node_ba_load.csv.gz` disaggregate the hourly EIA-930
demand of each US WECC balancing authority (BA) to the counties it serves,
in proportion to each county's hourly contribution to the BA's estimated
load, and then allocate the county loads to the WECC 240 nodes. The inputs
are copied from `eudoxys/loads` at commit `LOADS_COMMIT` (see
`wecc240_data.py`).

```mermaid
flowchart TD
    loads_ba["loads/_test/data/WECC_BA_hourly_load_2018-2022.csv"] -->|UTC hour-beginning| ba_load
    loads_county_ba["loads/wecc/county_ba.csv (EIA-861 2018)"] --> county_ba
    loads_node_cf["loads/wecc/node_estimate_cf.csv"] -->|cf → factor| county_node_factor
    loads_estimate["loads/wecc/wecc_estimate.csv.gz"] --> sum4((+))
    loads_dg["loads/wecc/county_dg_scaled.csv.gz"] -->|-| sum4
    sum4 -->|clip ≥ 0| county_estimate

    county_estimate --> mul4((x))
    county_ba -->|f_cb| mul4
    mul4 -->|"f_cb L_c / Σ_k f_kb L_k"| mul5((x))
    ba_load -->|D_b| mul5
    mul5 -->|Σ BA| county_ba_load

    county_ba_load --> mul6((x))
    county_node_factor -->|g_cn| mul6
    mul6 -->|Σ county| node_ba_load

    subgraph data/wecc240_data.py
        ba_load
        county_ba
        county_node_factor
        county_estimate
        county_ba_load
        node_ba_load
        sum4((+))
        mul4((x))
        mul5((x))
        mul6((x))
    end
```

Files:

- `ba_load.csv.gz`: cleaned EIA-930 hourly demand (MW) of the 28 US WECC
  BAs that report demand, `timestamp` UTC hour-beginning, 2018-2022 (the
  first 8 hours of 2018 are missing in the source).
- `county_ba.csv`: fraction of each county's load served by each BA
  (`county_st`, `ba`, `factor`, `method`).
- `county_node_factor.csv`: fraction of each county's load allocated to each
  node (`county_st`, `node`, `factor`, `method`).
- `county_ba_load.csv.gz`: county hourly net load (MW) disaggregated from
  EIA-930.
- `node_ba_load.csv.gz`: node hourly net load (MW) disaggregated from
  EIA-930 (113 US-load nodes, by geohash).

Checks (2018-2022): for every hour with EIA-930 data, the total node load
equals the EIA-930 WECC US total plus the uncalibrated share of the counties
served by `SWPP` (about 3 TWh/y) to within rounding; no node load is
negative.

| Year | EIA-930 TWh | Node TWh | Node peak MW |
|---|---|---|---|
| 2018 | 728.6 | 731.6 | 139,897 |
| 2019 | 718.7 | 721.7 | 133,141 |
| 2020 | 718.1 | 721.1 | 141,287 |
| 2021 | 724.7 | 727.6 | 136,203 |
| 2022 | 744.2 | 747.1 | 143,500 |
