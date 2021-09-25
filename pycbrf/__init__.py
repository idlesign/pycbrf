from .banks import Banks
from .currencies import Currency, Currencies
from .rate_dynamics import ExchangeRateDynamics
from .rates import ExchangeRates

VERSION = (1, 1, 0)
"""Application version number tuple."""

VERSION_STR = '.'.join(map(str, VERSION))
"""Application version number string."""
