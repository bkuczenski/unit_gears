from synonym_dict import SynonymSet, SynonymDict

MEASURES = ('catch', 'scaling', 'operation')  # note: ad hoc measures of specific gear or dissipation models are not managed


class Quantity(SynonymSet):
    def __init__(self, measure, name, unit, *args):
        assert measure in MEASURES
        self._measure = measure
        super(Quantity, self).__init__(name, *args)
        self._unit = str(unit)

    @property
    def unit(self):
        return self._unit

    @property
    def object(self):
        return self

    @property
    def measure(self):
        return self._measure


class QuantityGroup(SynonymDict):
    _entry_group = 'Quantities'
    _syn_type = Quantity

    _ignore_case = True

    _measure = None

    def __init__(self, measure, **kwargs):
        assert measure in MEASURES
        self._measure = measure
        super(QuantityGroup, self).__init__(**kwargs)

    @property
    def group(self):
        return self._measure

    def new_entry(self, *args, **kwargs):
        super(QuantityGroup, self).new_entry(self._measure, *args, **kwargs)
