# WECC 240 PSSE Model

```mermaid
flowchart LR
  nlrmodels[NLR models] --> wecc240_psse.raw
  wecc240_psse.raw --> raw2py.py --> validation[Model validation]
  raw2py.py --> wecc240_psse.py
```
