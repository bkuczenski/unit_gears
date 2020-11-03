"""
A model is something that converts an input to an output. Our base model is a generic n-order model of one variable,
for which each parameter can be either static or uncertain.
"""

from stats_arrays import (UncertaintyBase, MCRandomNumberGenerator, NormalUncertainty, LognormalUncertainty, \
    UniformUncertainty, TriangularUncertainty, NoUncertainty)

from math import log


class EmptyModel(Exception):
    """
    Models should have at least one parameter
    """
    pass


class InoperableModel(Exception):
    """
    Discrete models must be 0-order because they cannot take parameters
    """
    pass


class PolynomialModel(object):
    def _make_stats_array_input(self, arg):
        try:
            typ = arg[0].lower()[0]  # ignore typos (and i18n) with this simple trick!
            mean = float(arg[1])
            if typ == 'n':
                d = {'loc': float(arg[1]), 'scale': float(arg[2]), 'minimum': 0.0, 'uncertainty_type': NormalUncertainty.id}
            elif typ == 'l':  # take log of the data
                d = {'loc': log(float(arg[1])), 'scale': float(arg[2]), 'uncertainty_type': LognormalUncertainty.id}
            elif typ == 'u':
                d = {'maximum': float(arg[1]), 'minimum': float(arg[2]), 'uncertainty_type': UniformUncertainty.id}
                mean = (d['maximum'] + d['minimum']) / 2
            elif typ == 't':
                d = {'loc': float(arg[1]), 'maximum': float(arg[2]), 'minimum': float(arg[3]), 'uncertainty_type': TriangularUncertainty.id}
            elif type == 's':
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
            NormalUncertainty.id: 'N',
            LognormalUncertainty.id: 'L',
            TriangularUncertainty.id: 'T',
            UniformUncertainty.id: 'U'
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

    def __init__(self, *args):
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
        """
        if len(args) == 0:
            raise EmptyModel()
        if isinstance(args[0], str):
            # 0-order uncertain model specified with positional params
            args = self._re_parse_args(args)
        self._params = []
        self._means = []
        for arg in args:
            self._make_stats_array_input(arg)

        self._mcg = MCRandomNumberGenerator(UncertaintyBase.from_dicts(*self._params))

    @property
    def order(self):
        return len(self._params) - 1

    def _compute(self, x, arr):
        y = arr[0]
        for i in range(self.order):
            y += arr[i+1] * x**(i+1)
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
        return ';'.join(['%d:%.3g %s' % (i, self._means[i], self._p_str(k)) for i, k in enumerate(self._params)])

    def __str__(self):
        return 'y ~ %s (x)' % self._coef

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._coef)


class DiscreteChoiceRequired(Exception):
    pass


class DiscreteModel(object):
    """
    A mapping of discrete params to 0-order models, with or without uncertainty
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
