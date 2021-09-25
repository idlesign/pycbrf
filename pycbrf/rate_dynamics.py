from datetime import date, datetime
from decimal import Decimal
from logging import getLogger
from typing import Dict, Tuple, Union
from xml.etree import ElementTree

from .constants import URL_BASE
from .currencies import Currency, CURRENCIES
from .exceptions import ExchangeRateNotFound, WrongArguments
from .rates import ExchangeRate
from .utils import FormatMixin, WithRequests

LOG = getLogger(__name__)


class ExchangeRateDynamics(WithRequests, FormatMixin):
    """Receives and stores exchange rates for one currency over a period of time

    :param date_from: Start date of the period for the exchange rate dynamics.
    :param date_to: End date of the period for the exchange rate dynamics.
    :param currency: The currency for which the exchange rates were requested.
    :param rates: Dictionary of ExchangeRate parsed from the server.

    :Example:

    Creation:
        rates = ExchangeRateDynamics(currency='USD')
        rates = ExchangeRateDynamics('2021-08-24', currency='usd')
        rates = ExchangeRateDynamics(date(2021, 8, 24), currency='R01235')
        rates = ExchangeRateDynamics(datetime(2021, 8, 24, 0, 0), currency='r01235')
        rates = ExchangeRateDynamics('2021-08-01', date(2021, 8, 24), currency='840')
        rates = ExchangeRateDynamics(date_from='2021-08-24', currency=840)
    Receiving:
        By string: 4217 currency alphabetic code: rates('2021-08-24')
        By Python date: rates(date(2021, 08, 24))
        By Python datetime: rates(datetime(2021, 08, 24))

    .. note:: The Central Bank of Russia does not change rates on weekends and holidays.
        Sunday and Monday rates are the same as Saturday rates, but not available.
        The exchange rates on holidays are the same as on the last business day before the holiday, but not available.
        Exchange rates on such dates will not be available in the ExchangeRatesDynamics.
    """

    def __init__(self,
                 date_from: Union[str, date, datetime, None] = None,
                 date_to: Union[str, date, datetime, None] = None,
                 *,
                 currency: Union[str, int, Currency],
                 ):
        """
        :param date_from: Date of the exchange rate or start date of the period for the exchange rate dynamics.
            Python date and datetime objects and ISO date '%Y-%m-%d' string are supported.
        :param date_to: End date of the period for the exchange rate dynamics.
            Python date and datetime objects and ISO date '%Y-%m-%d' string are supported.
        :param currency: Currency for which you need to know the rate.
            Strings like ISO numeric code, ISO code or code the Bank of Russia or Currency instance are supported.

        .. note:: If all arguments are specified, get the rate dynamics between the passed dates.
            If currency and one date are passed, get the rate of the specified currency at the date.
            If only currency is passed, get the exchange rate for today.
        """

        self.date_from, self.date_to, self.currency = self._check_and_convert_args(date_from, date_to, currency)

        raw_data = self._get_data(self.currency)
        rates = self._parse(raw_data, self.currency)

        self.rates = rates

    def __getitem__(self, item: Union[str, date, datetime]) -> ExchangeRate:
        """Returns the ExchangeRate by date

        Python date and datetime objects or '%Y-%m-%d' ISO date string are supported.
        """
        if not item:
            raise WrongArguments(f"Args must be ISO code, numeric code, code the Bank of Russia of currency, "
                                 f"Currency instance, datetime.date or  or '%Y-%m-%d' ISO date string."
                                 f"Not {'None' if item is None else 'empty string'}.")

        key = self._datetime_from_string(item)

        try:
            return self.rates[key]
        except KeyError:
            raise ExchangeRateNotFound()

    def _check_and_convert_args(self,
                                date_from: Union[str, date, datetime, None],
                                date_to: Union[str, date, datetime, None],
                                currency: Union[str, int, Currency]
                                ) -> Tuple[datetime, datetime, Currency]:
        """Checks arguments and converts them to proper formats from strings and integer"""
        date_from = self._datetime_from_string(date_from)
        date_to = self._datetime_from_string(date_to)

        if not currency:
            raise WrongArguments('You must specify a currency if you want to get a range of currency rates.')

        if not date_from and not date_to:  # if both dates are empty
            today = date.today()
            date_from = date_to = datetime(today.year, today.month, today.day)  # datetime for unification
        elif bool(date_from) ^ bool(date_to):  # if any of the dates, but not both (XOR)
            date_from = date_to = next(filter(lambda x: x, (date_from, date_to)))

        if date_to < date_from:
            raise WrongArguments('The end date of the period must be later than the start date.')

        if currency and not isinstance(currency, Currency):
            currency: Currency = CURRENCIES[currency]

        return date_from, date_to, currency

    def _get_data(self, currency: Currency) -> bytes:
        """Prepares parameters for the link and returns raw XML"""
        url = f"{URL_BASE}XML_dynamic.asp"
        params = {
            'date_req1': self.date_from.strftime('%d/%m/%Y'),
            'date_req2': self.date_to.strftime('%d/%m/%Y'),
            'VAL_NM_RQ': currency.id,
        }

        response = super()._get_response(url=url, params=params)
        raw_data = response.content

        return raw_data

    @staticmethod
    def _parse(data: bytes, currency: Currency) -> Dict[datetime, ExchangeRate]:
        """Parse raw XML strings with rate dynamics to the dict of ExchangeRate"""
        LOG.debug('Parsing data ...')

        xml = ElementTree.fromstring(data)

        result = {}

        for child in xml:
            params = {}
            for param in child:
                params[param.tag] = param.text

            date_received = datetime.strptime(child.attrib['Date'], '%d.%m.%Y')
            par = Decimal(params['Nominal'])
            value = Decimal(params['Value'].replace(',', '.'))

            result[date_received] = ExchangeRate(
                currency=currency,
                name=currency.name_eng,
                on_date=date_received,
                par=par,
                value=value,
                rate=value / par,
            )

        LOG.debug(f"Parsed: {len(result)} days")

        return result

    def __str__(self):
        return f"{self.currency.code} ExchangeRateDynamics from {self.date_from} to {self.date_to}"

    def __len__(self):
        return len(self.rates)
