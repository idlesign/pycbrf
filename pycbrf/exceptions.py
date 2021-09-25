class PycbrfException(Exception):
    """Base exception."""


class WrongArguments(PycbrfException, TypeError):
    """The exception is raised if the passed arguments are insufficient or invalid"""

    def __init__(self, message=None):
        self.message = message


class CurrencyNotFound(PycbrfException, KeyError):
    """The exception is raised if Currency does not found in Currencies"""

    def __init__(self, message=None):
        self.message = message or 'There is no such currency within Currencies.'


class ExchangeRateNotFound(PycbrfException, KeyError):
    """The exception is raised if ExchangeRate does not found in ExchangeRates"""

    def __init__(self, message=None):
        self.message = message or 'There is no such ExchangeRate within ExchangeRates.'
