# WECC 240 models

## `wecc240_2011`

This model was produced by CAISO in 2011. The model does not require external data to load or run. This model is a static model with no time-series capabilities and can be run in `pypower` or `pypower_sim`.

## `wecc240_2018`

This model was produced by NREL in 2018. The model is based on the `wecc240_2011` model with the `scheduling.py` script run to apply modifications to the generation fleet. This model is a static model with no time-series capabilities and can be run in `pypower` or `pypower_sim`.

## `wecc240_2020`

This model was produced by NRL in 2026. The model is based on the `wecc240_2018` model with the `aggregate_load.py` and `aggregate_gens.py` scripts run to apply
modifications to the loads and generation resources.  This model a quasi-steady time-series model designed to be run using `pypower_sim`. 
