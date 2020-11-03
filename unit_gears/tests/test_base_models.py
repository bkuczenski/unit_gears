import unittest

from ..base_models import PolynomialModel, DiscreteModel, InoperableModel, EmptyModel


class BaseModelsTest(unittest.TestCase):
    """
    Note that we are not implementing any tests as to the correctness of the distributions
    """
    def test_static_0_order(self):
        sm = PolynomialModel(43.2)
        self.assertEqual(sm.mean(), 43.2)
        self.assertEqual(sm.sample(), 43.2)

    def test_uncertain_0_order_strict(self):
        sm = PolynomialModel(('normal', 17.5, 2.3))
        self.assertEqual(sm.order, 0)
        self.assertEqual(sm.mean(), 17.5)
        self.assertNotEqual(sm.sample(), 17.5)

    def test_uncertain_1_order_sloppy(self):
        a0, a0s = 33.2, 1.1
        a1, a1s = 0.54, 0.02
        a1mean = (a1 + a1s) / 2

        sm = PolynomialModel('normal', a0, a0s, 'uniform', a1, a1s)
        self.assertEqual(sm.order, 1)
        self.assertEqual(sm.mean(), a0)
        self.assertEqual(sm.mean(35), a0 + 35*a1mean)
        self.assertNotEqual(sm.sample(333), sm.mean(333))

    def test_static_higher_order(self):
        ps = [1, 2.3, 0.456, 0.789]
        sm = PolynomialModel(*ps)
        x = 4.2
        y = 0.0
        for i in range(len(ps)):
            y += ps[i]*x**i
        self.assertEqual(sm.mean(x), y)

    def test_mixed_certain_uncertain(self):
        sm = PolynomialModel(-3.4, ('normal', 7.1, 2.1), .25)
        self.assertEqual(sm.order, 2)
        self.assertEqual(sm.mean(1), -3.4 + 7.1 + .25)
        self.assertEqual(sm.mean(2), -3.4 + 14.2 + 1)
        self.assertNotEqual(sm.sample(1), sm.mean(1))

    def test_init_list(self):
        sm = PolynomialModel(["triangular", 0.066, 0.073, 0.059])
        self.assertEqual(sm.order, 0)

    def test_lognormal_validity(self):
        """
        just confirms that we are specifying the lognormal dist and not the base normal dist
        """
        a0, a1 = 350, 0.000001
        sm = PolynomialModel('lognormal', a0, a1)
        self.assertEqual(sm.mean(), a0)
        self.assertAlmostEqual(sm.mean(), sm.sample(), places=1)

    def test_empty(self):
        with self.assertRaises(EmptyModel):
            PolynomialModel()

    def test_inop(self):
        with self.assertRaises(InoperableModel):
            DiscreteModel(some=(45, 37))

    def test_discrete(self):
        dm = DiscreteModel(some=35, others=45)
        self.assertTupleEqual(dm.valid_params, ('others', 'some'))
        self.assertEqual(dm.mean('others'), 45)
        self.assertEqual(dm.sample('some'), 35)


if __name__ == '__main__':
    unittest.main()
