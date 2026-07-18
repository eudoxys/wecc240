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

    subgraph data/wecc240_data.py
        counties
        states
        bus_gis
        bustype_load_US
        node_dg
        state_mwh
        county_total
        county_node_map
        node_total
        county_node_cf
        county_dg

        mul1((x))
        mul2((x))
    end
```