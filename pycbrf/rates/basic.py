from datetime import date, datetime
from decimal import Decimal
from logging import getLogger
from typing import Dict, NamedTuple, Optional, Union
from xml.etree import ElementTree

from .constants import URL_BASE
from .currencies import Currency, CURRENCIES
from ..exceptions import CurrencyNotFound, ExchangeRateNotFound, WrongArguments
from ..utils import FormatMixin, WithRequests

LOG = getLogger(__name__)


class ExchangeRate(NamedTuple):
    """Represents exchange rate for the currency on the date

    :param date: Date of the exchange rate.
    :param currency: Currency for which the rate is fetched.
    :param value: Official exchange rates on selected date against the ruble.
    :param par: Nominal exchange rate.
    :param rate: Reduced exchange rate rate = value / par.
    """

    on_date: datetime
    currency: Currency
    name: str  # exists for backward compatibility.

    @property
    def id(self):
        return self.currency.id

    @property
    def name_ru(self):
        return self.currency.name_ru

    @property
    def name_eng(self):
        return self.currency.name_eng

    @property
    def code(self):
        return self.currency.code

    @property
    def num(self):
        return self.currency.num

    value: Decimal
    par: Decimal
    rate: Decimal


class ExchangeRates(WithRequests, FormatMixin):

    def __init__(self, on_date: Union[str, date, datetime, None] = None, locale_en: bool = False):
        """Fetches exchange rates.

        :Example:

        Various creation options are supported:

        rates = ExchangeRates()  # for today
        rates = ExchangeRates(date(2021, 08, 24))
        rates = ExchangeRates(on_date=datetime(2021, 08, 24, 0, 0))
        rates = ExchangeRates('2016-06-26', locale_en=True)

        Various indexing is supported:

        rates['USD']  # By ISO alpha code
        rates['R01235']  # By internal Bank of Russia code
        rates['840']  # By ISO numeric code.

        .. note:: The Central Bank of Russia does not change rates on weekends and holidays.
            The Sunday and Monday rates is set as equal as Saturday rate.
            The rates of holiday is set as equal as rates on the first working day after the holidays.

        :param on_date: Date to get rates for.
            Python date objects and ISO date string are supported.
            If not set rates on latest available date will be returned (usually tomorrow).

        :param locale_en: Flag to get currency names in English.
            If not set names will be provided in Russian.
        """

        if on_date:
            on_date = self._datetime_from_string(on_date)
        else:
            today = date.today()
            on_date = datetime(today.year, today.month, today.day)  # For backward compatibility, the time is 00:00

        raw_data = self._get_data(on_date, locale_en)
        parsed = self._parse(raw_data, locale_en)

        self.date_requested = on_date
        """Date requested by user."""

        self.date_received: datetime = parsed['date']
        """Date returned by Bank of Russia."""

        self.rates: Dict[Currency, ExchangeRate] = parsed['rates']
        """Rates fetched from server as a list."""

        self.dates_match: bool = (self.date_requested == self.date_received)

    def __getitem__(self, item: Union[str, int, Currency]) -> Optional[ExchangeRate]:
        """Implement dictionary lookup

        :param item: Bank of Russia code, numeric or alphabetic currency code according to ISO, Currency instance
        :return: The ExchangeRate instance for the requested currency
        """
        try:
            key: Optional[Currency] = CURRENCIES[item]
        except (WrongArguments, CurrencyNotFound):
            return None  # return None, not an exception, is made for backward compatibility.

        try:
            return self.rates[key]
        except ExchangeRateNotFound:
            return None  # return None, not an exception, is made for backward compatibility.

    @staticmethod
    def _parse(data: bytes, locale_en: bool) -> Dict[str, Union[datetime, Dict[Currency, ExchangeRate]]]:
        """Parse raw XML strings to the dict of BetaExchangeRates"""
        LOG.debug('Parsing data ...')

        xml = ElementTree.fromstring(data)
        meta = xml.attrib

        result = {
            'date': datetime.strptime(meta['Date'], '%d.%m.%Y'),
            'rates': {},
        }

        for currency in xml:
            props = {}
            for prop in currency:
                props[prop.tag] = prop.text

            par = Decimal(props['Nominal'])
            par_value = Decimal(props['Value'].replace(',', '.'))

            try:
                currency = CURRENCIES[currency.attrib['ID']]
            except CurrencyNotFound:
                # The request for old information may contain a currency
                # that has already been removed from the Currencies.
                # In this case, add a new currency to Currencies.
                currency = Currency(id=currency.attrib['ID'],
                                    name_eng=props['Name'],
                                    name_ru=props['Name'],
                                    code=props['CharCode'],
                                    num=props['NumCode'],
                                    par=Decimal(props['Nominal']),
                                    )
                CURRENCIES.add(currency)

            name = currency.name_eng if locale_en else currency.name_ru

            result['rates'][currency] = ExchangeRate(
                on_date=result['date'],
                currency=currency,
                name=name,
                value=par_value,
                par=par,
                rate=par_value / par,
            )

        LOG.debug(f"Parsed: {len(result['rates'])} currencies")

        return result

    @classmethod
    def _get_data(cls, on_date: datetime, locale_en: bool) -> bytes:
        """Prepares parameters for the link and returns raw XML"""
        url = f"{URL_BASE}XML_daily{'_eng' if locale_en else ''}.asp"

        params = {
            'date_req': on_date.strftime('%d/%m/%Y')
        }

        LOG.debug(f'Getting exchange rates from {url} ...')

        response = cls._get_response(url=url, params=params)
        data = response.content

        return data

    def __str__(self):
        return f"ExchangeRates of {len(self.rates)} currencies from {self.date_requested}"

    def __len__(self):
        return len(self.rates)
