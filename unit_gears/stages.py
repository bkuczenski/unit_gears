"""
Stages have a lot of features in common. They all [each] have models, for instance.

Note that a "unit of effort" is composed of [scaling unit] * [operation unit]


Common to all models:
 * name - basically a unique identifier-- should I make an external_ref as well??? ans: not internally
 * gear_types - a dict of Family: Entry or Family: [entry1, entry2..] that passes validate_gear_types()
 * model: a valid model
 - documentation - free text
 - ref_unit - a reference unit for the input flow. This is catch_unit for effort models, scaling_unit for gear models,
   and op_unit for dissipation models.
 - param_unit: quantity of the model input parameter. Must be supplied if model order > 0. can be any quantity.
 - param_max: input parameter value above which the model is invalid
 - param_min: input parameter value below which the model is invalid

Effort Models also specify downstream outputs:
 + catch_unit: a quantity measuring catch
 + scaling_unit: a quantity measuring the scale of the operation- may or may not be the same as param_unit
 + op_unit: a quantity measuring operation
 + op_equiv: a dict of { quantity: amount of that quantity that is equivalent to 1 op_unit}
 : model maps catch in catch_unit to effort in scaling_unit * op_unit
 : op_equiv example: op_unit is 1 fishing day, op_equiv could be 6 fishing hours or 0.01 years
 : op_factor(unit) returns the op_equiv directly, or 1.0 for unit == op_unit. this is multiplied by the result
   This is because we are converting op_unit to op_equiv

Gear Models add:
 + scaling_unit: a quantity measuring the scale of the operation- may or may not be the same as param_unit
 + attributes: dict of { ad hoc gear measure: amount per kg_gear }
 : model maps scaling_unit to kg_gear
 : if param_unit is omitted but required, it is assumed to be scaling_unit

Dissipation Models add:
 + op_unit: a quantity measuring operation
 + dissipation_type: ad hoc dissipation measure
 + op_equiv: a dict of { quantity: amount of that quantity that is equivalent to 1 op_unit
 : model maps op_unit to fraction dissipation
 : if param_unit is omitted but required, it is assumed to be op_unit
 : op_factor(unit) returns the inverse of op_equiv, or 1.0 for unit == op_unit. this is multiplied by the result.
   This is because we are converting op_equiv to op_unit


"""
from .base_models import PolynomialModel, DiscreteModel, DiscreteChoiceRequired, BaseModel
from .gear_mapping import validate_gear_types

from random import choice

class ModelAlreadyDefined(Exception):
    pass


class ModelStage(object):
    stage = None
    _param_valid = None
    ref_quantity = None

    def __init__(self, family, name, gear_types, model, _equiv, param_unit=None, param_min=None, param_max=None,
                 param_scale=None,
                 documentation=None, source_doc=None):
        """

        :param family:
        :param name:
        :param gear_types:
        :param model:
        :param _equiv:
        :param param_unit:
        :param param_min:
        :param param_max:
        :param param_scale:
        :param documentation:
        :param source_doc:
        """

        self.family = family
        self.name = name
        self.gear_ecs = set(validate_gear_types(gear_types))
        self.gear_types = gear_types

        if param_unit is None:
            if self.ref_quantity is not None:
                param_unit = getattr(self, self.ref_quantity)

        self.param_unit = param_unit
        self.param_min = param_min
        self.param_max = param_max
        self.param_scale = param_scale

        if _equiv is None:
            _equiv = dict()
        _equiv[self._equiv_unit.name] = 1.0

        self._equiv = _equiv

        self._doc = '\n'.join([(source_doc or "(No source documentation)"), documentation])

        self._model = self._parse_arg(model)
        if self._model.order > 0 and self.param_unit is None:
            print('%s: Warning: unspecified unit for required input parameter' % self.name)

    def __repr__(self):
        return '%s(%s: %d%s)[%s]'% (self.__class__.__name__, self.name, self.order, self.model_type[0], self.family)

    @property
    def _equiv_unit(self):
        return self.ref_unit

    def _get_cf(self, key):
        try:
            return next(v for k, v in self._equiv.items() if key == k)
        except StopIteration:
            raise KeyError(key)

    @property
    def ref_unit(self):
        return getattr(self, self.ref_quantity)

    @property
    def doc(self):
        return self._doc

    @property
    def model_type(self):
        if self._param_valid is None:
            return 'null'
        elif bool(self._param_valid):
            return 'discrete'
        return 'continuous'

    @property
    def order(self):
        return self._model.order

    def mean(self, param=None):
        try:
            return self._model.mean(param)
        except DiscreteChoiceRequired:
            print(self.name)
            raise

    def sample(self, param=None):
        values = list(self.values(param))
        return self._model.sample(choice(values))

    @property
    def keys(self):
        if self.model_type == 'discrete':
            for v in self._param_valid:
                yield v
        elif self.model_type == 'continuous':
            yield self.param_unit

    def values(self, param):
        """
        Generates all valid parameter values consistent with the input argument.

        For Continuous model types: Param can be:
         - None -> for 0-order models, yield 0.0
         - a number -> interpreted as a number in param_unit
         - a set, list, or tuple of numbers -> each generated
         - a dict of {unit: number} pairs -> passed into _equiv and converted
         - a dict of {unit: tuple} pairs -> each item passed into _equiv and converted

         The general case is a tuple of numbers expressed in terms of param_unit

        For Discrete model types: Param can be:
         - None -> generate keys
         - a string -> generate if string is a valid key
         - a list, set, or tuple of strings -> generate intersection with keys
         - a dict of {key: bool} -> generate intersection of True keys with keys

         The general case is a tuple of members of keys

        This is brilliant but deserves maybe a modicum of testing.

        :param param:
        :return:
        """
        if self.model_type == 'continuous':
            if isinstance(param, set) or isinstance(param, list) or isinstance(param, tuple):
                _gen = (float(k) for k in param if self.is_valid(k))
            elif isinstance(param, dict):
                if self._equiv_unit == self.param_unit:  # conversion is valid
                    _gen = []
                    for k, v in param.items():
                        try:
                            factor = self._equiv[k]
                        except KeyError:
                            continue
                        _gen.extend([t / factor for t in self.values(v)])
                else:
                    try:
                        _gen = self.values(param[self.param_unit])
                    except KeyError:
                        _gen = ()
            else:
                _gen = (k for k in (param, ) if self.is_valid(k))
        elif self.model_type == 'discrete':
            if param is None:
                _gen = self.keys
            else:
                if isinstance(param, dict):
                    param = [k for k, v in param.items() if bool(v)]
                if isinstance(param, set) or isinstance(param, list) or isinstance(param, tuple):
                    _gen = (k for k in param if self.is_valid(k))
                else:
                    _gen = (k for k in (param, ) if self.is_valid(k))
        else:
            _gen = ()

        for p in _gen:
            yield p

    def is_valid(self, param_value=None):
        """
        For qualitative models, 'param_value' must be in self.keys
        for quantitative models, if order > 0, value must be in bounds
        :param param_value:
        :return:
        """
        if self.model_type == 'null':
            return False
        if self.model_type == 'continuous':
            if self._model.order == 0:
                return True
            else:
                try:
                    value = float(param_value)
                except (TypeError, ValueError):
                    return False
                if self.param_min is not None:
                    if value < self.param_min:
                        return False
                if self.param_max is not None:
                    if value > self.param_max:
                        return False
                    return True
                return True
        if self.model_type == 'discrete':
            return param_value in self._param_valid
        return False

    def _parse_discrete(self, arg):
        dm = DiscreteModel(**arg)
        keys = dm.valid_params
        self._param_valid = keys
        return dm

    def _parse_arg(self, arg):
        """
        Three possibilities:
         - a single number
         - an iterable whose first entry is a string (uncertainty spec)
         - an iterable whose first entry is a non-string iterable
        :param arg:
        :return: either arg
        """
        if isinstance(arg, BaseModel):
            return arg
        if self.model_type != 'null':
            raise ModelAlreadyDefined()
        if arg is None:
            arg = 1.0
        if isinstance(arg, dict):
            return self._parse_discrete(arg)
        self._param_valid = []
        try:
            first = arg[0]
        except TypeError:
            # not indexable- just a number
            return PolynomialModel(arg, scale=self.param_scale)
        if isinstance(first, str):
            # uncertainty spec
            return PolynomialModel(arg, scale=self.param_scale)
        # higher-order model
        return PolynomialModel(*arg, scale=self.param_scale)


class CatchEffort(ModelStage):
    stage = 'effort'

    @property
    def ref_unit(self):
        return self.catch_unit

    def __init__(self, family, name, gear_types, catch_unit, scaling_unit, op_unit, effort_model, op_equiv=None, **kwargs):
        self.catch_unit = catch_unit
        self.scaling_unit = scaling_unit
        self.op_unit = op_unit

        super(CatchEffort, self).__init__(family, name, gear_types, effort_model, op_equiv, **kwargs)


    @property
    def _equiv_unit(self):
        return self.op_unit

    @property
    def op_units(self):
        """
        generates operation units
        :return:
        """
        for k in self._equiv.keys():
            yield k

    def op_factor(self, op_unit):
        return self._get_cf(op_unit)


class GearIntensity(ModelStage):
    stage = 'gear'
    ref_quantity = 'scaling_unit'

    def __init__(self, family, name, gear_types, scaling_unit, intensity_model, scaling_equiv=None,
                 attributes=None, **kwargs):
        self.scaling_unit = scaling_unit
        super(GearIntensity, self).__init__(family, name, gear_types, intensity_model, scaling_equiv, **kwargs)

        if attributes is None:
            attributes = dict()
        self.attributes = attributes

    @property
    def scaling_units(self):
        """
        generates operation units
        :return:
        """
        for k in self._equiv.keys():
            yield k

    def scaling_factor(self, scaling_unit):
        return self._get_cf(scaling_unit)


class Dissipation(ModelStage):
    stage = 'dissipation'
    ref_quantity = 'op_unit'

    def __init__(self, family, name, gear_types, op_unit, dissipation_type, dissipation_model, op_equiv=None, **kwargs):
        self.op_unit = op_unit
        self.dissipation_type = dissipation_type
        super(Dissipation, self).__init__(family, name, gear_types, dissipation_model, op_equiv, **kwargs)

    @property
    def op_units(self):
        """
        generates operation units
        :return:
        """
        for k in self._equiv.keys():
            yield k

    def op_factor(self, op_unit):
        return self._get_cf(op_unit)
