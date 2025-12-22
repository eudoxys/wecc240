import unittest

from wecc240.wecc240_2011 import WECC240_2011
from pypower_sim import PPModel, PPSolver

class TestWECC240(unittest.TestCase):
    
    def test_wecc240_2011(self):
        model = WECC240_2011()
        solver = PPSolver(model)
        self.assertTrue(solver.solve_opf())
        self.assertTrue(solver.solve_pf())

if __name__ == '__main__':
    unittest.main()