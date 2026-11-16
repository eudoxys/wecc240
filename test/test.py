import unittest

from wecc240.wecc240_2011 import wecc240_2011
from wecc240.wecc240_2018 import wecc240_2018
from pypower_sim import PPModel, PPSolver

class TestWECC240(unittest.TestCase):

    def test_wecc240_2011(self):
        # the 2011 case has no generator costs, so only the power flow applies
        model = PPModel(name="wecc240_2011",case=wecc240_2011)
        solver = PPSolver(model)
        self.assertTrue(solver.solve_pf())

    def test_wecc240_2018(self):
        model = PPModel(name="wecc240_2018",case=wecc240_2018)
        solver = PPSolver(model)
        self.assertTrue(solver.solve_opf())
        self.assertTrue(solver.solve_pf())

if __name__ == '__main__':
    unittest.main()
