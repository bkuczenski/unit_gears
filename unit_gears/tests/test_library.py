import unittest
from ..model_library import GearModelLibrary, MODELS_DIR
from ..base_models import DiscreteChoiceRequired


class TestGearLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gml = GearModelLibrary()

    def test_0_num_quantities(self):
        self.assertEqual(len(list(self.gml.quantities('catch'))), 2)
        self.assertEqual(len(list(self.gml.quantities())), 21)

    def test_0_synonym(self):
        self.assertEqual(self.gml.get_quantity('Vessel length in meters'), self.gml.get_quantity('LOA'))

    def test_1_load_models(self):
        self.gml.load_path(MODELS_DIR)
        self.assertEqual(len(list(self.gml.effort_models())), 10)
        self.assertEqual(len(list(self.gml.gear_models())), 13)
        self.assertEqual(len(list(self.gml.dissipation_models())), 23)

    def test_2_compose(self):
        k = list(self.gml.valid_models(gear_types={'GFWClass': 'trawlers'}))
        self.assertEqual(len(k), 9)
        with self.assertRaises(DiscreteChoiceRequired):
            [j.mean() for j in k]

    def test_3_mean(self):
        k = list(self.gml.valid_models(gear_types={'GFWClass': 'trawlers'}, gear_family='Watanabe'))
        self.assertEqual(len(k), 3)
        self.assertSetEqual({7.55625, 17.0625, 43.875}, set(j.mean() for j in k))


if __name__ == '__main__':
    unittest.main()
