"""Read the scheduling data and generate the 2018 model

Usage
-----

    python3 scheduling.py

Description
-----------

Running this script tests the 
"""

import warnings

import pandas as pd
import numpy as np

class Generator(pd.DataFrame):
    """Generator data frame implementation"""

    SCHEDULEFILE = __file__.replace("/scheduling.py","/data/WECC240_2018_Generation_scheduling.xlsx")
    """Schedule data file"""

    COLUMNS = ["busname","genname","Pmin","Pmax","Gen_Type",
        "InitStatus","InitPow","SUCost","SDCost","No_Load_Cost","Ramp_Rate",
        "Cost1","MW1","Cost2","MW2","Cost3","MW3","Cost4","MW4",
        ]
    """Columns to read from data file"""

    def __init__(self,
        file:str|None=None,
        ):
        """Construct generator schedule data frame"""
        data = pd.read_excel(self.SCHEDULEFILE if file is None else file,
            sheet_name="Generator",
            usecols=self.COLUMNS,
            )
        super().__init__(data[self.COLUMNS].sort_values(["busname","genname"]))

    def to_ppgen(self,
        basemva:float=100.0,
        q_factor:float=0.2,
        ) -> np.array:
        """Convert data frame to pypower gen array

        Arguments
        ---------

          - `basemva`: base MVA to use when converting from schedule data to
            PyPoWwer `gen` array

          - `q_factor`: reactive power fraction relative to real power
        Returns
        -------

          - `np.array`: gen data array for PyPower
        """
        return np.array([
            self.busname, # GEN_BUS
            self.InitPow, # PG
            np.zeros(len(self)), # QG
            self.Pmax*q_factor, # QMAX
            -self.Pmax*q_factor, # QMIN
            np.zeros(len(self)), # VG
            np.full(len(self),basemva), # MBASE
            self.InitStatus, # GEN_STATUS
            self.Pmax, # PMAX
            self.Pmin, # PMIN
            np.zeros(len(self)), # PC1
            np.zeros(len(self)), # PC2
            np.zeros(len(self)), # QC1MIN
            np.zeros(len(self)), # QC1MAX
            np.zeros(len(self)), # QC2MIN
            np.zeros(len(self)), # QC2MAX
            self.Ramp_Rate, # RAMP_AGC
            np.zeros(len(self)), # RAMP_10
            np.zeros(len(self)), # RAMP_30
            np.zeros(len(self)), # RAMP_Q
            np.zeros(len(self)), # APG
            np.zeros(len(self)), # MU_PMAX
            np.zeros(len(self)), # MU_PMIN
            np.zeros(len(self)), # MU_QMAX
            np.zeros(len(self)), # MU_QMIN
            ]).T

    def to_ppgencost(self,
        basemva:float=100.0,
        ):
        """Convert data frame to pypower gencost array"""
        cost1ok = (self.Cost1 > 0.0) | (self.MW1 > 0.0)
        if not cost1ok.all():
            warnings.warn("generation cost data contain f(0)=0 values")
        cost2ok = (self.Cost2 > self.Cost1) & (self.MW2 > self.MW1)
        cost3ok = cost2ok & (self.Cost3 > self.Cost2) & (self.MW3 > self.MW2)
        cost4ok = cost3ok & (self.Cost4 > self.Cost3) & (self.MW4 > self.MW3)
        return np.array([
            np.ones(len(self)),
            self.SUCost,
            self.SDCost,
            1+cost2ok+cost3ok+cost4ok,
            self.MW1,
            self.Cost1,
            self.MW2 * cost2ok.astype(int),
            self.Cost2 * cost2ok.astype(int),
            self.MW3 * cost3ok.astype(int),
            self.Cost3 * cost3ok.astype(int),
            self.MW4 * cost4ok.astype(int),
            self.Cost4 * cost4ok.astype(int),
            ]).T

class Storage(pd.DataFrame):
    """Energy storage data frame implementation"""

    SCHEDULEFILE = "data/WECC240_2018_Generation_scheduling.xlsx"
    """Schedule data file"""

    COLUMNS = None
    """Columns to read from data file"""

    def __init__(self,
        file:str|None=None,
        ):
        """Construct energy storage data frame"""
        data = pd.read_excel(self.SCHEDULEFILE if file is None else file,
            sheet_name="ESS",
            usecols=self.COLUMNS,
            index_col=0,
            )
        if self.COLUMNS is None:
            self.COLUMNS = data.columns
        super().__init__(data[self.COLUMNS].sort_values(["busname","essname"]))

class Line(pd.DataFrame):
    """Line data frame implementation"""

    SCHEDULEFILE = "data/WECC240_2018_Generation_scheduling.xlsx"
    """Schedule data file"""

    COLUMNS = None
    """Columns to read from data file"""

    def __init__(self,
        file:str|None=None,
        ):
        """Construct line data frame"""
        data = pd.read_excel(self.SCHEDULEFILE if file is None else file,
            sheet_name="Line",
            usecols=self.COLUMNS,
            )
        data.loc[data["FlowLim"]==99999,"FlowLim"] = 0
        if self.COLUMNS is None:
            self.COLUMNS = data.columns
        super().__init__(data[self.COLUMNS].sort_values(["StartBusName","EndBusName"]))

if __name__ == "__main__":

    pd.options.display.width = None
    pd.options.display.max_columns = None
    pd.options.display.max_rows = None
    
    gendata = Generator()
    assert len(gendata) == 197, "incorrect number of generators"
    
    gen = pd.DataFrame(gendata.to_ppgen().round(3),columns=[
        "GEN_BUS","PG","QG","QMAX","QMIN","VG","MBASE","GEN_STATUS",
        "PMAX","PMIN","PC1","PC2","QC1MIN","QC1MAX","QC2MIN","QC2MAX",
        "RAMP_AGC","RAMP_10","RAMP_30","RAMP_Q","APF",
        "MU_PMAX","MU_PMIN","MU_QMAX","MU_QMIN",
        ])
    gen.GEN_BUS = gen.GEN_BUS.astype(int)
    gen.GEN_STATUS = gen.GEN_STATUS.astype(int)
    assert gen.shape == (197,25), f"{gen.shape=} is not correct, expected (197,25)"

    gencost = pd.DataFrame(gendata.to_ppgencost().round(2),columns=[
        "MODEL","STARTUP","SHUTDOWN","NCOST",
        "COST0","COST1","COST2","COST3","COST4","COST5","COST6","COST7",
        ])
    gencost.MODEL = gencost.MODEL.astype(int)
    gencost.NCOST = gencost.NCOST.astype(int)
    assert gencost.shape == (197,12), f"{gencost.shape=} is not correct, expected (197,12)"

    assert len(Line()) == 451, "incorrect number of lines"

    assert len(Storage()) == 4, "incorrect number of storage systems"
    
