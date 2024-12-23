"""
IHyperStrategy interface, hyperoptable Parameter class.
This module defines a base class for auto-hyperoptable strategies.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from contextlib import suppress
from typing import Any, Union

from freqtrade.enums import HyperoptState
from freqtrade.optimize.hyperopt_tools import HyperoptStateContainer


with suppress(ImportError):
    from skopt.space import Categorical, Integer, Real

    from freqtrade.optimize.space import SKDecimal

from freqtrade.exceptions import OperationalException


logger = logging.getLogger(__name__)


class BaseParameter(ABC):
    """
    Defines a parameter that can be optimized by hyperopt.
    """

    category: str | None
    default: Any
    value: Any
    in_space: bool = False
    name: str

    def __init__(
        self,
        *,
        default: Any,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize hyperopt-optimizable parameter.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
         parameter field
         name is prefixed with 'buy_' or 'sell_'.
        :param optimize: Include parameter in hyperopt optimizations.
        :param load: Load parameter value from {space}_params.
        :param kwargs: Extra parameters to skopt.space.(Integer|Real|Categorical).
        """
        if "name" in kwargs:
            raise OperationalException(
                "Name is determined by parameter field name and can not be specified manually."
            )
        self.category = space
        self._space_params = kwargs
        self.value = default
        self.optimize = optimize
        self.load = load

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value})"

    @abstractmethod
    def get_space(self, name: str) -> Union["Integer", "Real", "SKDecimal", "Categorical"]:
        """
        Get-space - will be used by Hyperopt to get the hyperopt Space
        """

    def can_optimize(self):
        return (
            self.in_space
            and self.optimize
            and HyperoptStateContainer.state != HyperoptState.OPTIMIZE
        )


class NumericParameter(BaseParameter):
    """Internal parameter used for Numeric purposes"""

    float_or_int = int | float
    default: float_or_int
    value: float_or_int

    def __init__(
        self,
        low: float_or_int | Sequence[float_or_int],
        high: float_or_int | None = None,
        *,
        default: float_or_int,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize hyperopt-optimizable numeric parameter.
        Cannot be instantiated, but provides the validation for other numeric parameters
        :param low: Lower end (inclusive) of optimization space or [low, high].
        :param high: Upper end (inclusive) of optimization space.
                     Must be none of entire range is passed first parameter.
        :param default: A default value.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
                      parameter fieldname is prefixed with 'buy_' or 'sell_'.
        :param optimize: Include parameter in hyperopt optimizations.
        :param load: Load parameter value from {space}_params.
        :param kwargs: Extra parameters to skopt.space.*.
        """
        if high is not None and isinstance(low, Sequence):
            raise OperationalException(f"{self.__class__.__name__} space invalid.")
        if high is None or isinstance(low, Sequence):
            if not isinstance(low, Sequence) or len(low) != 2:
                raise OperationalException(f"{self.__class__.__name__} space must be [low, high]")
            self.low, self.high = low
        else:
            self.low = low
            self.high = high

        super().__init__(default=default, space=space, optimize=optimize, load=load, **kwargs)


class StepParameter(NumericParameter):
    """
    Parameter that can be optimized with fixed steps between values.
    Inherits from NumericParameter to maintain compatibility with the optimization framework.
    """

    default: int
    value: int
    low: int
    high: int
    step: int

    def __init__(
        self,
        low: int | Sequence[int],
        high: int | None = None,
        step: int = 1,
        *,
        default: int,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize step parameter with fixed intervals.

        :param low: Lower bound (inclusive) or [low, high] sequence
        :param high: Upper bound (inclusive), must be None if range passed as sequence
        :param step: Step size between values
        :param default: Default value
        :param space: Parameter category (e.g. 'buy' or 'sell')
        :param optimize: Include parameter in optimization
        :param load: Load parameter from space_params
        :param kwargs: Extra parameters for skopt.space.Integer
        """
        # Initialize parent class first to set up low/high values
        super().__init__(
            low=low, high=high, default=default, space=space, optimize=optimize, load=load, **kwargs
        )

        if step <= 0:
            raise OperationalException(f"Step must be positive, got {step}")

        if (self.high - self.low) % step != 0:
            raise OperationalException(
                f"Range {self.high - self.low} must be divisible by step {step}"
            )

        self.step = step

        # Validate default value
        if (default - self.low) % step != 0:
            raise OperationalException(f"Default value {default} does not match step size {step}")

    def get_space(self, name: str) -> "Integer":
        """
        Create skopt optimization space.
        :param name: Name of parameter field
        """
        return Integer(low=self.low, high=self.high, name=name, **self._space_params)

    @property
    def range(self):
        """
        Get valid values as range.
        Returns all possible values in optimize mode,
        otherwise returns just the current value.
        """
        if self.can_optimize():
            return range(self.low, self.high )
        else:
            return range(self.value, self.value + 1)

    def __repr__(self):
        """String representation including step size"""
        return f"{self.__class__.__name__}(value={self.value}, step={self.step})"


class IntParameter(NumericParameter):
    default: int
    value: int
    low: int
    high: int

    def __init__(
        self,
        low: int | Sequence[int],
        high: int | None = None,
        *,
        default: int,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize hyperopt-optimizable integer parameter.
        :param low: Lower end (inclusive) of optimization space or [low, high].
        :param high: Upper end (inclusive) of optimization space.
                     Must be none of entire range is passed first parameter.
        :param default: A default value.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
                      parameter fieldname is prefixed with 'buy_' or 'sell_'.
        :param optimize: Include parameter in hyperopt optimizations.
        :param load: Load parameter value from {space}_params.
        :param kwargs: Extra parameters to skopt.space.Integer.
        """

        super().__init__(
            low=low, high=high, default=default, space=space, optimize=optimize, load=load, **kwargs
        )

    def get_space(self, name: str) -> "Integer":
        """
        Create skopt optimization space.
        :param name: A name of parameter field.
        """
        return Integer(low=self.low, high=self.high, name=name, **self._space_params)

    @property
    def range(self):
        """
        Get each value in this space as list.
        Returns a List from low to high (inclusive) in Hyperopt mode.
        Returns a List with 1 item (`value`) in "non-hyperopt" mode, to avoid
        calculating 100ds of indicators.
        """
        if self.can_optimize():
            # Scikit-optimize ranges are "inclusive", while python's "range" is exclusive
            return range(self.low, self.high + 1)
        else:
            return range(self.value, self.value + 1)


class RealParameter(NumericParameter):
    default: float
    value: float

    def __init__(
        self,
        low: float | Sequence[float],
        high: float | None = None,
        *,
        default: float,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize hyperopt-optimizable floating point parameter with unlimited precision.
        :param low: Lower end (inclusive) of optimization space or [low, high].
        :param high: Upper end (inclusive) of optimization space.
                     Must be none if entire range is passed first parameter.
        :param default: A default value.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
                      parameter fieldname is prefixed with 'buy_' or 'sell_'.
        :param optimize: Include parameter in hyperopt optimizations.
        :param load: Load parameter value from {space}_params.
        :param kwargs: Extra parameters to skopt.space.Real.
        """
        super().__init__(
            low=low, high=high, default=default, space=space, optimize=optimize, load=load, **kwargs
        )

    def get_space(self, name: str) -> "Real":
        """
        Create skopt optimization space.
        :param name: A name of parameter field.
        """
        return Real(low=self.low, high=self.high, name=name, **self._space_params)


class DecimalParameter(NumericParameter):
    default: float
    value: float

    def __init__(
        self,
        low: float | Sequence[float],
        high: float | None = None,
        *,
        default: float,
        decimals: int = 3,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize hyperopt-optimizable decimal parameter with a limited precision.
        :param low: Lower end (inclusive) of optimization space or [low, high].
        :param high: Upper end (inclusive) of optimization space.
                     Must be none if entire range is passed first parameter.
        :param default: A default value.
        :param decimals: A number of decimals after floating point to be included in testing.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
                      parameter fieldname is prefixed with 'buy_' or 'sell_'.
        :param optimize: Include parameter in hyperopt optimizations.
        :param load: Load parameter value from {space}_params.
        :param kwargs: Extra parameters to skopt.space.Integer.
        """
        self._decimals = decimals
        default = round(default, self._decimals)

        super().__init__(
            low=low, high=high, default=default, space=space, optimize=optimize, load=load, **kwargs
        )

    def get_space(self, name: str) -> "SKDecimal":
        """
        Create skopt optimization space.
        :param name: A name of parameter field.
        """
        return SKDecimal(
            low=self.low, high=self.high, decimals=self._decimals, name=name, **self._space_params
        )

    @property
    def range(self):
        """
        Get each value in this space as list.
        Returns a List from low to high (inclusive) in Hyperopt mode.
        Returns a List with 1 item (`value`) in "non-hyperopt" mode, to avoid
        calculating 100ds of indicators.
        """
        if self.can_optimize():
            low = int(self.low * pow(10, self._decimals))
            high = int(self.high * pow(10, self._decimals)) + 1
            return [round(n * pow(0.1, self._decimals), self._decimals) for n in range(low, high)]
        else:
            return [self.value]


class CategoricalParameter(BaseParameter):
    default: Any
    value: Any
    opt_range: Sequence[Any]

    def __init__(
        self,
        categories: Sequence[Any],
        *,
        default: Any | None = None,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize hyperopt-optimizable parameter.
        :param categories: Optimization space, [a, b, ...].
        :param default: A default value. If not specified, first item from specified space will be
         used.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
         parameter field
         name is prefixed with 'buy_' or 'sell_'.
        :param optimize: Include parameter in hyperopt optimizations.
        :param load: Load parameter value from {space}_params.
        :param kwargs: Extra parameters to skopt.space.Categorical.
        """
        if len(categories) < 2:
            raise OperationalException(
                "CategoricalParameter space must be [a, b, ...] (at least two parameters)"
            )
        self.opt_range = categories
        super().__init__(default=default, space=space, optimize=optimize, load=load, **kwargs)

    def get_space(self, name: str) -> "Categorical":
        """
        Create skopt optimization space.
        :param name: A name of parameter field.
        """
        return Categorical(self.opt_range, name=name, **self._space_params)

    @property
    def range(self):
        """
        Get each value in this space as list.
        Returns a List of categories in Hyperopt mode.
        Returns a List with 1 item (`value`) in "non-hyperopt" mode, to avoid
        calculating 100ds of indicators.
        """
        if self.can_optimize():
            return self.opt_range
        else:
            return [self.value]


class BooleanParameter(CategoricalParameter):
    def __init__(
        self,
        *,
        default: Any | None = None,
        space: str | None = None,
        optimize: bool = True,
        load: bool = True,
        **kwargs,
    ):
        """
        Initialize hyperopt-optimizable Boolean Parameter.
        It's a shortcut to `CategoricalParameter([True, False])`.
        :param default: A default value. If not specified, first item from specified space will be
         used.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
         parameter field
         name is prefixed with 'buy_' or 'sell_'.
        :param optimize: Include parameter in hyperopt optimizations.
        :param load: Load parameter value from {space}_params.
        :param kwargs: Extra parameters to skopt.space.Categorical.
        """

        categories = [True, False]
        super().__init__(
            categories=categories,
            default=default,
            space=space,
            optimize=optimize,
            load=load,
            **kwargs,
        )
