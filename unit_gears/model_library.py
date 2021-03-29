"""
The point of this class is two fold:
 - to collect and organize a set of UnitGearModels
 - to gather fisheries input data and marshall it together to run the models and generate results
 * related to the second goal is to handle stochastic simulations

The libraries themselves are de-serialized simply, but they must be *registered* with the model, including
with any model-specific designations for applicable fisheries or countries
"""

import json
import os
# from collections import defaultdict

from .quantities import QuantityGroup, MEASURES
from .gear_mapping import validate_gear_types
from .stages import CatchEffort, GearIntensity, Dissipation
from .query import GearModel, ConflictingUnits  # , ConflictingParams, NoValidParams  # , ZeroValuedModel


REFERENCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reference'))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models'))

MODEL_STAGES = ('effort', 'gear', 'dissipation')


class InvalidQuantity(Exception):
    pass


class GearModelLibrary(object):

    def _print(self, st, verbose=None):
        if verbose is None:
            verbose = self._verbose
        if verbose:
            print(st)

    def _load(self, lib_path, overwrite=False, verbose=None):
        # First load quantities
        if lib_path not in self._paths:
            self._paths.append(lib_path)
        self._load_quantities(lib_path, verbose=verbose)
        if len(list(self.quantities())) == 0:
            print('Note: no quantities found in path %s' % lib_path)
        for f in os.listdir(lib_path):
            family, ext = os.path.splitext(f)
            if ext.lower() != '.json':
                continue
            if family.lower() == 'quantities':
                continue
            try:
                self.load_family(lib_path, family, overwrite=overwrite, verbose=verbose)
            except json.JSONDecodeError:
                continue

    def load_family(self, lib_path, family, overwrite=False, verbose=None):
        if family.lower() == 'quantities':
            raise AttributeError('quantities.json is not a data family')
        with open(os.path.join(lib_path, family + '.json')) as fp:
            j = json.load(fp)
        source_doc = '\n'.join('%s: %s' %(k, v) for k, v in j.items() if k.startswith('source_'))
        self._load_effort(family, source_doc, j.pop('effort_models', []), overwrite=overwrite, verbose=verbose)
        self._load_gear(family, source_doc, j.pop('gear_models', []), overwrite=overwrite, verbose=verbose)
        self._load_diss(family, source_doc, j.pop('dissipation_models', []), overwrite=overwrite, verbose=verbose)

    def load_path(self, lib_path, overwrite=True, verbose=True):
        self._load(lib_path, overwrite=overwrite, verbose=verbose)

    def _load_quantities(self, lib_path, verbose=None):
        try:
            with open(os.path.join(lib_path, 'quantities.json')) as fp:
                j = json.load(fp)
        except FileNotFoundError:
            self._print('No quantities file in %s' % lib_path, verbose=verbose)
            return
        qdict = j.pop('quantities', [])
        if len(qdict) == 0:
            return
        for m in MEASURES:
            for qm in qdict.pop(m, []):
                self._print('Adding %s quantity %s' % (m, qm[0]), verbose=verbose)
                self._q[m].new_entry(*qm)

    def _load_effort(self, family, source_doc, entries, overwrite=False, verbose=None):
        for entry in entries:
            self._print('Adding effort model %s' % entry['name'], verbose=verbose)
            entry['catch_unit'] = self.get_quantity(entry.pop('catch_unit'), measure='catch')
            entry['scaling_unit'] = self.get_quantity(entry.pop('scaling_unit'), measure='scaling')
            entry['op_unit'] = self.get_quantity(entry.pop('op_unit'), measure='operation')
            e = CatchEffort(family, source_doc=source_doc, **entry)
            self.add_effort_model(e, overwrite=overwrite)

    def add_effort_model(self, e, overwrite=False):
        assert isinstance(e, CatchEffort)
        self._add_model(e, self._e, overwrite=overwrite)

    def _load_gear(self, family, source_doc, entries, overwrite=False, verbose=None):
        for entry in entries:
            self._print('Adding gear intensity model %s' % entry['name'], verbose=verbose)
            entry['scaling_unit'] = self.get_quantity(entry.pop('scaling_unit'), measure='scaling')
            g = GearIntensity(family, source_doc=source_doc, **entry)
            self.add_gear_model(g, overwrite=overwrite)

    def add_gear_model(self, g, overwrite=False):
        assert isinstance(g, GearIntensity)
        self._add_model(g, self._g, overwrite=overwrite)

    def _load_diss(self, family, source_doc, entries, overwrite=False, verbose=False):
        for entry in entries:
            self._print('Adding dissipation model %s' % entry['name'], verbose=verbose)
            entry['op_unit'] = self.get_quantity(entry.pop('op_unit'), measure='operation')
            d = Dissipation(family, source_doc=source_doc, **entry)
            self.add_dissipation_model(d, overwrite=overwrite)

    def add_dissipation_model(self, d, overwrite=False):
        assert isinstance(d, Dissipation)
        self._add_model(d, self._d, overwrite=overwrite)

    @staticmethod
    def _add_model(m, target, overwrite=False):
        if m.name in target:
            if overwrite:
                print('Overwriting model %s' % m.name)
            else:
                print('Not overwriting model %s' % m.name)
                return
        target[m.name] = m

    def __init__(self, *paths, verbose=False, **kwargs):
        """

        :param gears_path: folder containing
        :param kwargs:

        """
        self._verbose = verbose

        self._q = {m: QuantityGroup(m) for m in MEASURES}
        self._args = kwargs
        self._e = dict()
        self._g = dict()
        self._d = dict()
        self._paths = []
        self._load(REFERENCE_DIR, verbose=verbose)
        for lib_path in paths:
            self._load(lib_path, verbose=verbose)

    def _yield_from_meas(self, meas):
        for k in sorted(self._q[meas].objects, key=lambda x: x.name):
            yield self._q[meas][k]

    def quantities(self, measure=None):
        if measure is not None:
            if measure in self._q:
                for q in self._yield_from_meas(measure):
                    yield q
            else:
                yield ValueError('Unknown measure %s' % measure)
        else:
            for meas in MEASURES:
                for q in self._yield_from_meas(meas):
                    yield q

    def get_quantity(self, name, measure=None):
        q = None
        if measure is None or measure not in MEASURES:
            for v in self._q.values():
                try:
                    q = v[name]
                except KeyError:
                    continue
        else:
            q = self._q[measure][name]
        if q is None:
            raise InvalidQuantity(name)
        return q

    @property
    def effort_names(self):
        for k in sorted(self._e.keys()):
            yield k

    @property
    def gear_names(self):
        for k in sorted(self._g.keys()):
            yield k

    @property
    def dissipation_names(self):
        for k in sorted(self._d.keys()):
            yield k

    @staticmethod
    def _check_model(mod, ec=None, family=None):
        if ec is not None:
            if not bool(mod.gear_ecs.intersection(ec)):
                return False
        if family is not None:
            if not mod.family.lower().startswith(family.lower()):
                return False
        return True

    def effort_models(self, ec=None, family=None, effort=None):
        try:
            v = self._e[effort]
            if self._check_model(v, ec=ec, family=family):
                yield v
        except KeyError:
            for k in self.effort_names:
                v = self._e[k]
                if self._check_model(v, ec=ec, family=family):
                    yield v

    def gear_models(self, ec=None, family=None, gear=None):
        try:
            v = self._g[gear]
            if self._check_model(v, ec=ec, family=family):
                yield v
        except KeyError:
            for k in self.gear_names:
                v = self._g[k]
                if self._check_model(v, ec=ec, family=family):
                    yield v

    def dissipation_models(self, ec=None, family=None, dissipation=None):
        try:
            v = self._d[dissipation]
            if self._check_model(v, ec=ec, family=family):
                yield v
        except KeyError:
            for k in self.dissipation_names:
                v = self._d[k]
                if self._check_model(v, ec=ec, family=family):
                    yield v

    def valid_models(self, gear_types, verbose=None,
                     effort=None, gear=None, dissipation=None,
                     effort_family=None, gear_family=None, dissipation_family=None):
        """
        Generate valid triples of (catch-effort, gear-intensity, dissipation) for the specified gear and parameters.
        {effort, gear, dissipation} = strict matching to name of desired model (still subject to gear type matching)
        {effort_family, gear_family, dissipation_family} = filter when family name starts with supplied string
        :param gear_types: a dict of {family: gear} or {family: [gear1, ...]}
        :param verbose:
        :param effort: literal name to only match
        :param gear: "
        :param dissipation: "
        :param effort_family: Filter by <family>.lower()startswith(<arg>.lower())
        :param gear_family: "
        :param dissipation_family: "
        :return:
        """
        ecs = set(validate_gear_types(gear_types))

        count = 0

        for eff in self.effort_models(ecs, family=effort_family, effort=effort):
            for gm in self.link_effort_model(eff, gear=gear, dissipation=dissipation,
                                             gear_family=gear_family, dissipation_family=dissipation_family,
                                             verbose=verbose, _ecs=ecs):
                self._print('%d: %s-%s-%s passed' % (count, eff, gm.gear, gm.dissipation), verbose=verbose)
                yield gm
                count += 1

    def link_effort_model(self, eff, gear=None, dissipation=None,
                          gear_family=None, dissipation_family=None, verbose=None, _ecs=None):
        """
        This allows externally-specified effort models to use library gear+dissipation models
        :param eff:
        :param gear:
        :param dissipation:
        :param gear_family:
        :param dissipation_family:
        :param verbose:
        :param _ecs: pass a more limiting set of
        :return:
        """
        if _ecs is None:
            _ecs = eff.gear_ecs
        for gea in self.gear_models(_ecs, family=gear_family, gear=gear):
            for dis in self.dissipation_models(_ecs, family=dissipation_family, dissipation=dissipation):
                try:
                    gm = GearModel(eff, gea, dis)
                except ConflictingUnits as e:
                    err = '%s: %s' % (e.__class__.__name__, e)
                    self._print('%s-%s-%s ... failed %s' % (eff, gea, dis, err), verbose=verbose)
                    continue
                yield gm

    @staticmethod
    def models_report(models, e_param=None, g_param=None, d_param=None):
        """
        :param models: an iterable of models, e.g. the output of valid_models
        :param e_param: effort param value used for report generation
        :param g_param: gear ""
        :param d_param: dissipation ""
        :return:
        """
        for mod in models:
            for report in mod.report(e_param=e_param, g_param=g_param, d_param=d_param):
                yield report
