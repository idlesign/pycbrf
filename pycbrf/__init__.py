from .banks import Banks
from .rates import Currency, Currencies, ExchangeRates, ExchangeRateDynamics

VERSION = (1, 1, 0)
"""Application version number tuple."""

VERSION_STR = '.'.join(map(str, VERSION))
"""Application version number string."""
