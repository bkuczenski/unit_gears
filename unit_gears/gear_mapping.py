"""
map between gear models
"""

import csv
import os
from collections import defaultdict
# from itertools import chain

MASTER_GEAR_FILE = os.path.join(os.path.dirname(__file__), 'reference', 'master_gear_mapping.csv')


class GearMapper(object):

    def _add_record(self, record):
        this = len(self._classes)
        self._classes.append(record)
        for k, v in record.items():
            v = v.strip()
            if k not in self._sectors:
                self._sectors[k] = list()
            if v not in self._sectors[k]:
                self._sectors[k].append(v)
            self._reverse[k, v].add(this)

    def __init__(self):
        self._sectors = dict()
        self._reverse = defaultdict(set)
        self._classes = []  # I want a dict, but like, where the keys are just automatically increasing whole numbers...
        with open(MASTER_GEAR_FILE) as f:
            _cr = csv.DictReader(f)
            for record in _cr:
                self._add_record(record)

    def _gather_eqs(self, d1):
        first = []
        for k, v in d1.items():
            if isinstance(v, str):
                first.extend(list(self._reverse[k, v]))
            else:
                for t in v:
                    first.extend(list(self._reverse[k, t]))
        return set(first)

    def overlap(self, d1, d2):
        """
        Generates equivalence classes where the two gear types overlap
        :param d1: a valid gear_types dict
        :param d2: a valid gear_types dict
        :return:
        """
        f1 = self._gather_eqs(d1)
        f2 = self._gather_eqs(d2)
        for x in f1.intersection(f2):
            yield x

    def test_equivalence(self, family, gear, mappings):
        """
        Returns a dict containing synonyms in mappings for family: gear
        :param family:
        :param gear:
        :param mappings: dict of family:gear specs
        :return:
        """
        is_true = dict()
        for k, v in mappings.items():
            if v in self.translate(family, gear, k):
                is_true[k] = v
        return is_true

    def validate_gear_type(self, family, gear):
        """

        :param family: must be a column heading in master_gear_mapping
        :param gear: must either be a string found in the column, or an iterable of strings found in the column
        :return:
        """
        sect = self._sectors[family]  # or key error
        if isinstance(gear, str):
            if gear in sect:
                return self._reverse[family, gear]
            raise ValueError('%s: %s|' % (family, gear))
        # assume gear is a list-like
        ecs = set()
        for g in gear:
            if g not in sect:
                raise ValueError('%s: %s|' % (family, g))
            for k in self.c_ids(family, g):
                ecs.add(k)
        return sorted(list(ecs))

    def translate(self, family, gear, query_family):
        """
        Given gear:family (e.g. FAOGearName:Handlines and pole-lines (mechanized)) provide a list of synonyms in
        a target family.
        :param family:
        :param gear:
        :param query_family:
        :return:
        """
        if query_family not in self.families:
            raise KeyError(query_family)
        if gear not in self._sectors[family]:
            raise ValueError(gear)

        s = set(self._classes[k][query_family] for k in self._reverse[family, gear])
        return s

    def sectors(self, family):
        return self._sectors[family]

    def equivs(self, family, gear):
        for c in self._reverse[family, gear]:
            yield self._classes[c]

    def c_ids(self, family, gear):
        for c in self._reverse[family, gear]:
            yield c

    @property
    def families(self):
        for k in self._sectors.keys():
            yield k


gear_mapper = GearMapper()


def validate_gear_types(gear_types):
    if not isinstance(gear_types, dict):
        raise TypeError('Gear Type specification must be a dict')
    c_ids = []
    for k, v in gear_types.items():
        c_ids.extend(gear_mapper.validate_gear_type(k, v))
    return sorted(list(set(c_ids)))


def test_overlap(g1, g2):
    try:
        next(gear_mapper.overlap(g1, g2))
    except StopIteration:
        return False
    return True
