"""
A model is something that converts an input to an output. Our base model is a generic n-order model of one variable,
for which each parameter can be either static or uncertain.
"""

from stats_arrays import (UncertaintyBase, MCRandomNumberGenerator, NormalUncertainty, LognormalUncertainty, \
    UniformUncertainty, TriangularUncertainty, NoUncertainty)

from math import log, exp


class EmptyModel(Exception):
    """
    Models should have at least one parameter
    """
    pass


class BaseModel(object):
    """
    Abstract model class
    """
    @property
    def order(self):
        raise NotImplementedError

    def mean(self, param):
        raise NotImplementedError

    def sample(self, param):
        raise NotImplementedError

    @property
    def valid_params(self):
        raise NotImplementedError


class InoperableModel(Exception):
    """
    Discrete models must be 0-order because they cannot take parameters

    This should not apply to multimodal continuous models [not yet implemented] where the param values are numeric
    and the model selection param is also used as the model input. In these cases, the keys would be ordered, and the
    model selected would be the least-greater-valued key.  The highest-valued key thus signifies an upper bound for
    the param.
    """
    pass


class PolynomialModel(BaseModel):
    _log = False
    _log10 = False

    def _make_stats_array_input(self, arg):
        """
        Strictly speaking, the order params for triangular distributions are specified is irrelevant, since they can
        be sorted.
        This is also true for uniform distributions.
        :param arg:
        :return:
        """
        try:
            typ = arg[0].lower()[0]  # ignore typos (and i18n) with this simple trick!
            mean = float(arg[1])
            if typ == 'n':
                d = {'loc': float(arg[1]), 'scale': float(arg[2]), 'uncertainty_type': NormalUncertainty.id}
                if self.bounded:
                    # bound normal distributions on the same side of 0 for stability purposes
                    if d['loc'] > 0:
                        d['minimum'] = d['loc'] / 1e3
                    elif d['loc'] < 0:
                        d['maximum'] = d['loc'] / 1e3
            elif typ == 'l':  # take log of the data
                d = {'loc': log(float(arg[1])), 'scale': float(arg[2]), 'uncertainty_type': LognormalUncertainty.id}
            elif typ == 'u':
                mn, mx = tuple(sorted(float(a) for a in arg[1:]))
                d = {'maximum': mx, 'minimum': mn, 'uncertainty_type': UniformUncertainty.id}
                mean = (mn + mx) / 2
            elif typ == 't':
                mn, lc, mx = tuple(sorted(float(a) for a in arg[1:]))
                d = {'loc': lc, 'maximum': mx, 'minimum': mn, 'uncertainty_type': TriangularUncertainty.id}
            elif typ == 's':
                d = {'loc': float(arg[1]), 'uncertainty_type': NoUncertainty.id}
            else:
                raise ValueError('Unknown uncertainty type %s' % arg[0])
        except (TypeError, IndexError):
            d = {'loc': float(arg), 'uncertainty_type': NoUncertainty.id}
            mean = float(arg)

        self._params.append(d)
        self._means.append(mean)

    @staticmethod
    def _p_str(k):
        return {
            NoUncertainty.id: '',
            NormalUncertainty.id: ' N',
            LognormalUncertainty.id: ' L',
            TriangularUncertainty.id: ' T',
            UniformUncertainty.id: ' U'
        }[k['uncertainty_type']]

    @staticmethod
    def _re_parse_args(args):
        args = list(args)
        orders = []
        while len(args) > 0:
            coef = [args.pop(0)]
            while len(args) > 0 and not isinstance(args[0], str):
                coef.append(args.pop(0))
            orders.append(tuple(coef))
        return orders

    def __init__(self, *args, bounded=True, scale=None):
        """
        Generate a polynomial model, with or without uncertainty.  The number of positional args determines the
        order of the model.

        I'm sure someone has done this better.

        To implement an uncertain model on *any* argument, the argument should be a tuple with the following format:
         ('normal', mean, stdev)  # note: will be bounded at 0
         ('lognormal', exp(mu), sigma)  # note: enter the true value of the mean, not mean of the underlying normal dist.
         ('uniform', high, low)
         ('triangular', mode, high, low)
         ('static', mean) # no uncertainty

        :param args:
        :param scale: None or default: polynomial models are linear in the parameter
         'log': Model applies to log-transformed data; the computation returns exp(result)
         'log10': Model applies to log10-transformed data; the computation returns 10**(result).
        :param bounded: [True] bound normal distributions on the same side of 0 as loc, for stability purposes.
        """
        if len(args) == 0:
            raise EmptyModel()
        if isinstance(args[0], str):
            # 0-order uncertain model specified with positional params
            args = self._re_parse_args(args)
        self.scale = scale
        self._params = []
        self._means = []
        self.bounded = bounded
        for arg in args:
            self._make_stats_array_input(arg)

        self._mcg = MCRandomNumberGenerator(UncertaintyBase.from_dicts(*self._params))

    @property
    def valid_params(self):
        return []

    @property
    def scale(self):
        if self._log:
            return 'log'
        elif self._log10:
            return 'log10'
        else:
            return 'linear'

    @scale.setter
    def scale(self, value):
        if value is None:
            return
        if value == 'log':
            self._log = True
            self._log10 = False
        elif value == 'log10':
            self._log10 = True
            self._log = False
        elif value == 'linear':
            self._log = self._log10 = False
        if self._log and self._log10:
            self._log = self._log10 = False
            raise ValueError('Cannot specify both log and log10')  # this should never happen

    @property
    def order(self):
        return len(self._params) - 1

    def _compute(self, x, arr):
        x = x or 0.0
        y = arr[0]
        for i in range(self.order):
            y += arr[i+1] * x**(i+1)
        if self._log:
            return exp(y)
        elif self._log10:
            return 10 ** y
        return y

    def mean(self, value=0.0):
        return self._compute(value, self._means)

    def sample(self, value=0.0):
        res = [float(k) for k in next(self._mcg)]
        return self._compute(value, res)

    @property
    def y_int(self):
        return self.mean(0.0)

    @property
    def _coef(self):
        return ';'.join(['%d:%.3g%s' % (i, self._means[i], self._p_str(k)) for i, k in enumerate(self._params)])

    @property
    def _exp(self):
        if self._log:
            return 'exp '
        elif self._log10:
            return '10 ** '
        else:
            return ''

    def __str__(self):
        return 'y ~ %s%s (x)' % (self._exp, self._coef)

    def __repr__(self):
        return '%s(%s%s)' % (self.__class__.__name__, self._exp, self._coef)


class DiscreteChoiceRequired(Exception):
    pass


class DiscreteModel(BaseModel):
    """
    A mapping of discrete params to 0-order models, with or without uncertainty. In a discrete model, a qualitative
    param (dict lookup) is used to select from a range of alternative models. The models must have 0-order because
    at the moment there is no mechanism to pass a second param to be used as the model input.
    """
    def __init__(self, **params):
        self._models = dict()
        for param, mdl in params.items():
            try:
                model = PolynomialModel(mdl)
            except AttributeError:
                raise InoperableModel('params: %s' % str(mdl))
            if model.order != 0:
                raise InoperableModel(param)
            self._models[param] = model

    @property
    def order(self):
        return 0

    @property
    def valid_params(self):
        return tuple(sorted(self._models.keys()))

    def mean(self, param):
        try:
            return self._models[param].mean()
        except KeyError:
            raise DiscreteChoiceRequired(self.valid_params)

    def sample(self, param):
        try:
            return self._models[param].sample()
        except KeyError:
            raise DiscreteChoiceRequired(self.valid_params)

    @property
    def _means(self):
        return '; '.join(['%s: %.3g' % (k, self.mean(k)) for k in self.valid_params])

    def __str__(self):
        return 'y : %s (x)' % self._means

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._means)
