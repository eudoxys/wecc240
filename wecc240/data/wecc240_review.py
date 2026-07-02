import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(r"""
    This notebook reviews the results of the WECC240 time-series simulation
    """)
    return


@app.cell
def _(PPModel):
    model = PPModel("case240_2020",case="../case240_2020.py")
    data = model.case
    return (model,)


@app.cell
def _(pd):
    PF = pd.read_csv("wecc240_branch_PF.csv",index_col=[0],parse_dates=[0])
    return (PF,)


@app.cell
def _(PF, branch, mo, model):
    # fractional line loading w.r.t line rating
    FR = PF.abs() / model.case["branch"][:, branch.RATE_A] * 100
    mo.mpl.interactive(
        FR.plot(
            grid=True,
            figsize=(10, 7),
            ylabel="Load flow (% rating)",
            xlabel="Date/Time",
            title="WECC240_2020",
        )
    )
    return


@app.cell
def _():
    # busmap = {int(y):x for x,y in enumerate(data["bus"][:,bus.BUS_I])}
    return


@app.cell
def _():
    # dict(enumerate((((x,y) for x,y in model.case["branch"][:,[branch.F_BUS,branch.T_BUS]].astype(int)))))
    return


@app.cell
def _():
    # branchmap = {y:x for x,y in enumerate(model.case["branch"][:,[branch.F_BUS,branch.T_BUS]].tolist())}
    return


@app.cell
def _():
    # puZ = data["baseMVA"] / data["bus"][:,bus.BASE_KV]**2
    # fbus = data["branch"][:,branch.F_BUS]
    return


@app.cell
def _():
    # OR_CA = {"AC":[(4001,8001),(3906,4001)],"DC":[(4010,2619)]}
    # for ltype,lines in OR_CA.items():
    #     for line in lines:
    #         print(ltype,model.case["branch"][[busmap[x] for x in line],["PF","QF","PT","QT"]])
    return


@app.cell
def _():
    import os
    import sys

    import marimo as mo
    import numpy as np
    import pandas as pd

    from pypower_sim import PPModel
    from pypower_sim.ppmodel import idx_bus as bus
    from pypower_sim.ppmodel import idx_branch as branch

    sys.path.append("..")
    return PPModel, branch, mo, pd


if __name__ == "__main__":
    app.run()
