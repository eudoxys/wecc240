# WECC 240 models

## `wecc240_2011`

This model was produced by CAISO in 2011. The model does not require external data to load or run. This model is a static model with no time-series capabilities and can be run in `pypower` or `pypower_sim`.

The static pseudo-DC line gen/load models in the 2011 model are converted to explicit DC lines and costs.

## `wecc240_2018`

This model was produced by NREL in 2018. The model is based on the `wecc240_2011` model with the `scheduling.py` script run to apply modifications to the generation fleet, line flow limits, and energy storage. This model is a static model with no time-series capabilities and can be run in `pypower` or `pypower_sim`.

### Energy Storage

The energy storage control strategy is scheduled based on the anticipated response to the "duck-curve" in CAISO, i.e., charging from 9am to 3pm, and discharging from 3pm to 9pm.

## `wecc240_2020`

This model was produced by NRL in 2026. The model is based on the `wecc240_2018` model with the `aggregate_load.py` and `aggregate_gens.py` scripts run to apply
modifications to the loads and generation resources.  This model a quasi-steady time-series model designed to be run using `pypower_sim`. 

### Load Curtailment

Load curtailment is implemented in three regimes:

1. During normal operations, no load curtailment is specified.
2. When node-level load is within 10% of the line import capacity plus generation of the node, "level 0" load curtailment is enabled, i.e., 10% of the load at the node is made available for curtailment.
3. When area-level load is within 15% of the line import capacity plus generation of the area, "level 1" load curtailment is enabled, i.e., 15% of the load in the area is made available for curtailment.

## `wecc240_2025`

This model was produced by LLNL in 2026 and reflects the system in Q3 2025. The model is based on the `wecc240_2020` model with updates for new generation and new loads, including data centers.
