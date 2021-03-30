try:
    from math import prod
except ImportError:
    from numpy import product as prod

from collections import namedtuple


SampleValue = namedtuple('SampleValue', ('effort', 'scaling_factor', 'gear', 'op_factor', 'dissipation'))


class SampleDetail(object):
    def __init__(self, effort, scaling_factor, gear, op_factor, dissipation):
        self.e_param, self.effort = effort
        self.g_param, self.gear = gear
        self.d_param, self.dissipation = dissipation
        self.scaling_factor = scaling_factor
        self.op_factor = op_factor
        self.gear_kg = self.effort * self.scaling_factor * self.gear * self.op_factor
        self.diss_kg = self.gear_kg * self.dissipation

    def __iter__(self):
        return iter(SampleValue(self.effort, self.scaling_factor, self.gear, self.op_factor, self.dissipation))


# SampleDetail = namedtuple('SampleDetail', ('effort', 'scaling_factor', 'gear', 'op_factor', 'dissipation'))


class ConflictingUnits(Exception):
    pass


class ConflictingParams(Exception):
    pass


class NoValidParams(Exception):
    pass


class ZeroValuedModel(Exception):
    pass


class GearModel(object):
    """
    Note on the directionality of unit conversions:

    Each stage is equipped with an "equivalence table" of quantities and their conversion factors with a unit of the
    fishing gear material flow. All the entries in an equivalence table correspond to the same amount, so units whose
    value is 1.0 are reference units.

    When two adjacent stages have different units, a conversion factor is applied. Traveling downstream, we divide by
    downstream equivalency factors or multiply by upstream ones.

    effort intensity: 0.4
    effort: vessel-set per catch    gear: mass per vessel meter    downstream: dissipation per year
    {set: 1.0                       {LOA: 1.0                      { year: 1.0
     hour: 6.0                       vessel:  0.04545                set: 120
     year: 0.005                    }                              }
    }
    A 22-meter vessel that catches 2.5 t per set has an effort intensity of 0.4 vessel-sets per tonne catch
    However, that same vessel has an effort intensity of 22*6 / 2.5 = 52.8 meter-hours per tonne.  Thus we multiply
    by the effort model's 6 hours per set equivalency and divide by the gear model's 0.0454545 vessels per meter.

    When we move on to dissipation per year, we get different results depending on which model we ask. The effort is
    consulted first (*0.005), but if the effort model doesn't know, the dissipation model is asked (/120)


    In the LCI case, the effort intensity is 1 ton of catch per ton of catch.  The gear intensity is direct: 580 g per
    ton, and some fraction of that 580 g is dissipated.  How much? the dissipation rate, per year. say 3%.  3% per year
    is, of course, 9% over the course of a gear's 3-year life, but for the year in question it's simply 3% of the mass.
    Thus

    n.b. I know family is not enough to uniquely identify models.

    """
    def __init__(self, e=None, g=None, d=None, label=None):
        self._e = e
        self._g = g
        self._d = d

        self.validate()

        self._label = label

    def validate(self):
        try:
            assert self.scaling_factor * self.op_factor != 0
        except AssertionError:
            raise ZeroValuedModel(self._e.family, self._g.family, self._d.family)

    @property
    def effort(self):
        return self._e

    @property
    def gear(self):
        return self._g

    @property
    def label(self):
        if self._label is None:
            fam = ['']
            for k in self.family:
                if k == fam[-1]:
                    continue
                fam.append(k)
            return '-'.join(fam[1:])
        return self._label

    @label.setter
    def label(self, title):
        self._label = str(title)

    @property
    def dissipation(self):
        return self._d

    def e_bar(self, param=None):
        return self._e.mean(param)

    def e_tilde(self, param=None):
        return self._e.sample(param)

    @property
    def scaling_unit(self):
        return self._e.scaling_unit

    def g_bar(self, param=None):
        return self._g.mean(param)

    def g_tilde(self, param=None):
        return self._g.sample(param)

    @property
    def op_unit(self):
        return self._e.op_unit

    def d_bar(self, param=None):
        return self._d.mean(param)

    def d_tilde(self, param=None):
        return self._d.sample(param)

    @property
    def family(self):
        return self._e.family, self._g.family, self._d.family

    @property
    def scaling_factor(self):
        """
        upstream is effort; downstream is gear. effort doesn't currently keep a scaling equiv (but should)
        :return:
        """

        if self._e.scaling_unit == self._g.scaling_unit:
            return 1.0
        elif self._e.scaling_unit in self._g.scaling_units:
            return 1.0 / self._g.scaling_factor(self._e.scaling_unit)
        else:
            raise ConflictingUnits('%s > %s' % (self._e.scaling_unit, list(self._g.scaling_units)))

    @property
    def op_factor(self):
        """
        upstream is effort; downstream is dissipation.
        :return:
        """
        if self._e.op_unit == self._d.op_unit:
            return 1.0
        elif self._d.op_unit in self._e.op_units:
            return self._e.op_factor(self._d.op_unit)
        elif self._e.op_unit in self._d.op_units:
            return 1.0 /  self._d.op_factor(self.op_unit)
        else:
            raise ConflictingUnits('%s > %s' % (list(self._e.op_units), list(self._d.op_units)))


    def _report_row(self, e_param, g_param, d_param):
        e, sf, g, of, d = self.mean_long(e_param=e_param, g_param=g_param, d_param=d_param)
        r = {
            'catch_family': self._e.family,
            'gear_family': self._g.family,
            'dissipation_family': self._d.family,
            'catch_unit': self._e.catch_unit.name,
            'scaling_unit': self.scaling_unit.name,
            'op_unit': self.op_unit.name,
            'effort_param': e_param,
            'effort': e,
            'scaling_factor': sf,
            'intensity_param': g_param,
            'intensity': g,
            'op_factor': of,
            'dissipation_op': self._d.op_unit.name,
            'dissipation_param': d_param,
            'dissipation': d,
            'dissipation_type': self._d.dissipation_type,
            'result': e*sf*g*of*d
        }

        r.update(self._g.attributes)
        return r

    def report(self, e_param=None, g_param=None, d_param=None):
        for ep in self._e.values(e_param):
            for gp in self._g.values(g_param):
                for dp in self._d.values(d_param):
                    yield self._report_row(ep, gp, dp)

    def mean_long(self, e_param=None, g_param=None, d_param=None):
        return SampleDetail(self.e_bar(e_param), self.scaling_factor, self.g_bar(g_param), self.op_factor, self.d_bar(d_param))

    def mean(self, e_param=None, g_param=None, d_param=None):
        return prod(self.mean_long(e_param=e_param, g_param=g_param, d_param=d_param))

    def sample_long(self, e_param=None, g_param=None, d_param=None):
        return SampleDetail(self.e_tilde(e_param), self.scaling_factor, self.g_tilde(g_param), self.op_factor, self.d_tilde(d_param))

    def sample(self, e_param=None, g_param=None, d_param=None):
        return prod(self.sample_long(e_param=e_param, g_param=g_param, d_param=d_param))

    def __str__(self):
        return "; ".join((self._e.name, self._g.name, self._d.name))

    @property
    def family(self):
        return self._e.family, self._g.family, self._d.family

    @property
    def formula(self):
        return "%s ~ %s * %s" % (self._e.catch_unit, self.scaling_unit, self.op_unit)

'''
class GearTraversal(GearModel):
    """
    What do you get when you traverse a gear model?
    """
    def __init__(self, gear_types, params=None, effort=None, gear=None, dissipation=None):
        super(GearTraversal, self).__init__()
        if params is None:
            params = dict()
        self.gear_ecs = 
        self.quals = set()
        self.quants = dict()

        for k, v in params.items():
            if v is True:
                self.quals.add(k)
            elif float(v) == v:
                self.quants[k] = v

        self.effort = effort
        self.gear = gear
        self.dissipation = dissipation

    def check_gear(self, mod):
        if self.gear_ecs.intersection(mod.gear_ecs):
            return True
        return False

    def _check_param(self, mod):
        if mod is None:
            return
        if mod.model_type == 'discrete':
            t = [k for k in self.quals if mod.is_valid(k)]
            if len(t) > 1:
                raise ConflictingParams()
            elif len(t) == 0:
                raise NoValidParams(list(mod.keys))
            return t[0]
        elif mod.model_type == 'continuous':
            if mod.order == 0:
                return None
            if mod.param_unit in self.quants:
                return self.quants[mod.param_unit]
            raise NoValidParams(mod.param_unit)

    @property
    def effort(self):
        return self._e

    @effort.setter
    def effort(self, mod):
        self._e_param = self._check_param(mod)
        self._e = mod

    @property
    def gear(self):
        return self._g

    @gear.setter
    def gear(self, mod):
        if mod is None:
            return
        if mod.scaling_unit != self.scaling_unit:
            raise ConflictingUnits('%s | %s' % (mod.scaling_unit, self.scaling_unit))
        self._g_param = self._check_param(mod)
        self._g = mod

    @property
    def dissipation(self):
        return self._d

    @dissipation.setter
    def dissipation(self, mod):
        if mod is None:
            return
        if mod.op_unit not in self._e.op_units and self._e.op_unit not in mod.op_units:
            raise ConflictingUnits('%s < %s' % (list(mod.op_units), list(self._e.op_units)))
        self._d_param = self._check_param(mod)
        self._d = mod

    def strip(self):
        return GearModel(self._e, self._e_param, self._g, self._g_param, self._d, self._d_param)

    def __str__(self):
        gm = next(list(self.gear_ecs)[0].values())
        return "%s: %s ~ %s%s" % (gm , self._e.catch_unit, self.scaling_unit, self.op_unit)
'''