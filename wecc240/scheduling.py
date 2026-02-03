"""Read the scheduling data and generate the 2018 model
"""

import pandas as pd
import numpy as np

class Generator(pd.DataFrame):
    """Generator data frame implementation"""

    SCHEDULEFILE = "data/WECC240_2018_Generation_scheduling.xlsx"
    """Schedule data file"""

    COLUMNS = ["busname","genname","Pmin","Pmax","Gen_Type",
        "InitStatus","SUCost","SDCost","No_Load_Cost",
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
        q_factor:float=1.0,
        ) -> np.array:
        """Convert data frame to pypower gen array

        Arguments
        ---------

          - `basemva`: base MVA to use when converting from schedule data to
            PyPoWwer `gen` array

        Returns
        -------

          - `np.array`: gen data array for PyPower
        """
        return np.array([
            self.busname.astype(int),
            np.zeros(len(self)),
            np.zeros(len(self)),
            self.Pmax*q_factor,
            -self.Pmax*q_factor,
            np.ones(len(self)),
            np.full(len(self),basemva),
            self.InitStatus,
            self.Pmax,
            self.Pmin,
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            np.zeros(len(self)),
            ]).T

    def to_ppgencost(self):
        """Convert data frame to pypower gencost array"""
        return np.array([
            np.ones(len(self)),
            self.SUCost,
            self.SDCost,
            (np.array([self.Cost2,self.Cost3,self.Cost4]).T>0).sum(axis=1)+1,
            self.Cost1,
            self.MW1,
            self.Cost2,
            self.MW2,
            self.Cost3,
            self.MW3,
            self.Cost4,
            self.MW4,
            ])

class ESS(pd.DataFrame):
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
        if self.COLUMNS is None:
            self.COLUMNS = data.columns
        super().__init__(data[self.COLUMNS].sort_values(["StartBusName","EndBusName"]))

if __name__ == "__main__":

    pd.options.display.width = None
    pd.options.display.max_columns = None
    
    gen = Generator()
    print(gen.to_ppgen())
    print(gen.to_ppgencost())
    # print(ESS())
    # print(Line())