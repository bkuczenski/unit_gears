import unittest
from ..model_library import GearModelLibrary, MODELS_DIR


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


if __name__ == '__main__':
    unittest.main()
