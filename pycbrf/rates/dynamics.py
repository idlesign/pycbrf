from datetime import date, datetime
from decimal import Decimal
from logging import getLogger
from typing import Dict, Tuple, Union
from xml.etree import ElementTree

from .constants import URL_BASE
from .currencies import Currency, CURRENCIES
from ..exceptions import ExchangeRateNotFound, WrongArguments
from .basic import ExchangeRate
from ..utils import FormatMixin, WithRequests, TypeDateDef

LOG = getLogger(__name__)


class ExchangeRateDynamics(WithRequests, FormatMixin):
    """Receives and stores exchange rates for one currency over a period of time

    :param since: Start date of the period for the exchange rate dynamics.
    :param till: End date of the period for the exchange rate dynamics.
    :param currency: The currency for which the exchange rates were requested.
    :param rates: Dictionary of ExchangeRate parsed from the server.

    .. code-block::

        # Creation:
            rates = ExchangeRateDynamics(currency='USD')
            rates = ExchangeRateDynamics('2021-08-24', currency='usd')
            rates = ExchangeRateDynamics(date(2021, 8, 24), currency='R01235')
            rates = ExchangeRateDynamics(datetime(2021, 8, 24, 0, 0), currency='r01235')
            rates = ExchangeRateDynamics('2021-08-01', date(2021, 8, 24), currency='840')
            rates = ExchangeRateDynamics(since='2021-08-24', currency=840)

    Receiving:
        By string: 4217 currency alphabetic code: rates('2021-08-24')
        By Python date: rates(date(2021, 08, 24))
        By Python datetime: rates(datetime(2021, 08, 24))

    .. note:: The Central Bank of Russia does not change rates on weekends and holidays.
        Sunday and Monday rates are the same as Saturday rates, but not available.
        The exchange rates on holidays are the same as on the last business day before the holiday, but not available.
        Exchange rates on such dates will not be available in the ExchangeRatesDynamics.
    """

    def __init__(
            self,
            since: TypeDateDef = None,
            till: TypeDateDef = None,
            *,
            currency: Union[str, int, Currency],
            locale_en: bool = False,
    ):
        """
        :param since: Date of the exchange rate or start date of the period for the exchange rate dynamics.
            Python date and datetime objects and ISO date '%Y-%m-%d' string are supported.

        :param till: End date of the period for the exchange rate dynamics.
            Python date and datetime objects and ISO date '%Y-%m-%d' string are supported.

        :param currency: Currency for which you need to know the rate.
            Strings like ISO numeric code, ISO code or code the Bank of Russia or Currency instance are supported.

        :param locale_en: Flag to get currency names in English.
            If not set names will be provided in Russian.

        .. note:: If all arguments are specified, get the rate dynamics between the passed dates.
            If currency and one date are passed, get the rate of the specified currency at the date.
            If only currency is passed, get the exchange rate for today.
        """

        self.since, self.till, self.currency = self._check_and_convert_args(since, till, currency)

        raw_data = self._get_data(self.currency)
        rates = self._parse(raw_data, self.currency, locale_en=locale_en)

        self.rates = rates

    def __getitem__(self, item: TypeDateDef) -> ExchangeRate:
        """Returns the ExchangeRate by date.

        Python date and datetime objects or '%Y-%m-%d' ISO date string are supported.
        """
        if not item:
            raise WrongArguments(
                "Args must be ISO code, numeric code, code the Bank of Russia of currency, "
                "Currency instance, datetime.date or  or '%Y-%m-%d' ISO date string."
                f"Not {'None' if item is None else 'empty string'}.")

        key = self._get_datetime(item)

        try:
            return self.rates[key]
        except KeyError:
            raise ExchangeRateNotFound()

    def _check_and_convert_args(
            self,
            since: TypeDateDef,
            till: TypeDateDef,
            currency: Union[str, int, Currency]

        ) -> Tuple[datetime, datetime, Currency]:
        """Checks arguments and converts them to proper formats from strings and integer"""
        since = self._get_datetime(since)
        till = self._get_datetime(till)

        if not currency:
            raise WrongArguments('You must specify a currency if you want to get a range of currency rates.')

        if not since and not till:  # if both dates are empty
            today = date.today()
            since = till = datetime(today.year, today.month, today.day)  # datetime for unification

        elif bool(since) ^ bool(till):  # if any of the dates, but not both (XOR)
            since = till = next(filter(lambda x: x, (since, till)))

        if till < since:
            raise WrongArguments('The end date of the period must be later than the start date.')

        if currency and not isinstance(currency, Currency):
            currency: Currency = CURRENCIES[currency]

        return since, till, currency

    def _get_data(self, currency: Currency) -> bytes:
        """Prepares parameters for the link and returns raw XML"""
        url = f"{URL_BASE}XML_dynamic.asp"
        format_date = self._date_format
        params = {
            'date_req1': format_date(self.since),
            'date_req2': format_date(self.till),
            'VAL_NM_RQ': currency.id,
        }

        response = super()._get_response(url=url, params=params)
        raw_data = response.content

        return raw_data

    @classmethod
    def _parse(cls, data: bytes, currency: Currency, *, locale_en: bool = False) -> Dict[datetime, ExchangeRate]:
        """Parse raw XML strings with rate dynamics to the dict of ExchangeRate"""
        LOG.debug('Parsing data ...')

        xml = ElementTree.fromstring(data)

        result = {}

        get_date = cls._date_parse

        for child in xml:
            params = {}
            for param in child:
                params[param.tag] = param.text

            date_received = get_date(child.attrib['Date'])
            par = Decimal(params['Nominal'])
            value = Decimal(params['Value'].replace(',', '.'))

            result[date_received] = ExchangeRate(
                currency=currency,
                name=currency.name_eng if locale_en else currency.name_ru,
                date=date_received,
                par=par,
                value=value,
                rate=value / par,
            )

        LOG.debug(f"Parsed: {len(result)} days")

        return result

    def __str__(self):
        return f"{self.currency.code} ExchangeRateDynamics from {self.since} to {self.till}"

    def __len__(self):
        return len(self.rates)
