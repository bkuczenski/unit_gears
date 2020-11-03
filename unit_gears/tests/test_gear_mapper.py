import unittest

from ..gear_mapping import validate_gear_types


class GearModelTest(unittest.TestCase):
    def test_valid_gear_type(self):
        self.assertTrue(validate_gear_types({'GFWClass': 'squid_jigger'}))

    def test_valid_gear_types(self):
        self.assertTrue(validate_gear_types({'VonBrandt3Code': ('7', '9.2', '5.6.3')}))

    def test_invalid_gear_type(self):
        with self.assertRaises(KeyError):
            validate_gear_types({'VonBrundtland': '42'})
        with self.assertRaises(ValueError):
            validate_gear_types({'VonBrandtDescription': ('7', '9.2', '5.6.3')})

    def test_fads(self):
        self.assertTrue(validate_gear_types({'FADs': "Purse Seine Anchored FADs"}))


if __name__ == '__main__':
    unittest.main()
