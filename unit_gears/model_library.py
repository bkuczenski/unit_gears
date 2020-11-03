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
        with open(os.path.join(lib_path, 'quantities.json')) as fp:
            j = json.load(fp)
            self._load_quantities(j.pop('quantities'))
        for f in os.listdir(lib_path):
            family, ext = os.path.splitext(f)
            if ext.lower() != '.json':
                continue
            if family.lower() == 'quantities':
                continue
            with open(os.path.join(lib_path, f)) as fp:
                try:
                    j = json.load(fp)
                except json.JSONDecodeError:
                    continue
                source_doc = '\n'.join('%s: %s' %(k, v) for k, v in j.items() if k.startswith('source_'))
                self._load_effort(family, source_doc, j.pop('effort_models', []), overwrite=overwrite, verbose=verbose)
                self._load_gear(family, source_doc, j.pop('gear_models', []), overwrite=overwrite, verbose=verbose)
                self._load_diss(family, source_doc, j.pop('dissipation_models', []), overwrite=overwrite, verbose=verbose)

    def load_all(self, lib_path, overwrite=True, verbose=True):
        self._load(lib_path, overwrite=overwrite, verbose=verbose)

    def _load_quantities(self, qdict):
        if len(qdict) == 0:
            return
        for m in MEASURES:
            for qm in qdict.pop(m, []):
                self._q[m].new_entry(*qm)

    def _load_effort(self, family, source_doc, entries, overwrite=False, verbose=None):
        for entry in entries:
            self._print('Adding effort model %s' % entry['name'], verbose=verbose)
            entry['catch_unit'] = self._q['catch'][entry.pop('catch_unit')]
            entry['scaling_unit'] = self._q['scaling'][entry.pop('scaling_unit')]
            entry['op_unit'] = self._q['operation'][entry.pop('op_unit')]
            e = CatchEffort(family, source_doc=source_doc, **entry)
            if e.name in self._e:
                if overwrite:
                    print('Overwriting model %s' % e.name)
                else:
                    print('Not overwriting model %s' % e.name)
                    continue
            self._e[e.name] = e

    def _load_gear(self, family, source_doc, entries, overwrite=False, verbose=None):
        for entry in entries:
            self._print('Adding gear intensity model %s' % entry['name'], verbose=verbose)
            entry['scaling_unit'] = self._q['scaling'][entry.pop('scaling_unit')]
            g = GearIntensity(family, source_doc=source_doc, **entry)
            if g.name in self._g:
                if overwrite:
                    print('Overwriting model %s' % g.name)
                else:
                    print('Not overwriting model %s' % g.name)
                    continue
            self._g[g.name] = g

    def _load_diss(self, family, source_doc, entries, overwrite=False, verbose=False):
        for entry in entries:
            self._print('Adding dissipation model %s' % entry['name'], verbose=verbose)
            entry['op_unit'] = self._q['operation'][entry.pop('op_unit')]
            d = Dissipation(family, source_doc=source_doc, **entry)
            if d.name in self._d:
                if overwrite:
                    print('Overwriting model %s' % d.name)
                else:
                    print('Not overwriting model %s' % d.name)
                    continue
            self._d[d.name] = d

    def __init__(self, lib_path, verbose=False, **kwargs):
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
        self._load(lib_path, verbose=verbose)

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

    def effort_models(self, ec=None, family=None):
        for k in self.effort_names:
            v = self._e[k]
            if self._check_model(v, ec=ec, family=family):
                yield v

    def gear_models(self, ec=None, family=None):
        for k in self.gear_names:
            v = self._g[k]
            if self._check_model(v, ec=ec, family=family):
                yield v

    def dissipation_models(self, ec=None, family=None):
        for k in self.dissipation_names:
            v = self._d[k]
            if self._check_model(v, ec=ec, family=family):
                yield v

    def valid_models(self, gear_types, verbose=None, effort_family=None, gear_family=None, dissipation_family=None):
        """
        Generate valid triples of (catch-effort, gear-intensity, dissipation) for the specified gear and parameters.
        :param gear_types: a dict of {family: gear} or {family: [gear1, ...]}
        :param verbose:
        :param effort_family: Filter by <family>.lower()startswith(<arg>.lower())
        :param gear_family: "
        :param dissipation_family: "
        :return:
        """
        ecs = set(validate_gear_types(gear_types))

        count = 0

        for eff in self.effort_models(ecs, family=effort_family):
            for gea in self.gear_models(ecs, family=gear_family):
                for dis in self.dissipation_models(ecs, family=dissipation_family):
                    try:
                        gm = GearModel(eff, gea, dis)
                    except ConflictingUnits as e:
                        err = '%s: %s' % (e.__class__.__name__, e)
                        self._print('%s-%s-%s ... failed %s' % (eff, gea, dis, err), verbose=verbose)
                        continue
                    self._print('%d: %s-%s-%s passed' % (count, eff, gea, dis), verbose=verbose)
                    yield gm
                    count += 1

    def models_report(self, models, e_param=None, g_param=None, d_param=None):
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
