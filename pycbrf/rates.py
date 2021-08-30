import datetime as dt
from decimal import Decimal
from logging import getLogger
from typing import Dict, NamedTuple, Optional, Tuple, Union
from xml.etree import ElementTree

from .exceptions import CurrencyNotFound, ExchangeRateNotFound, WrongArguments
from .utils import SingletonMeta, FormatMixin, WithRequests

LOG = getLogger(__name__)
URL_BASE = 'http://www.cbr.ru/scripts/'


class Currency(NamedTuple):
    """Represents a foreign currency.

    :param id: Internal code of the Bank of Russia.
    :param name_eng: Currency name in English.
    :param name_ru: Currency name in Russian.
    :param par: Nominal exchange rate.
    :param num: ISO 4217 currency numeric code.
    :param code: ISO 4217 currency alphabetic code.

    :Example:

    Currency(
        id='R01010',
        name_ru='Австралийский доллар',
        name_eng='Australian Dollar',
        num='036',
        code='AUD',
        par=Decimal('1'))
    """

    id: str
    name_eng: str
    name_ru: str
    num: str
    code: str
    par: Decimal

    def __hash__(self):
        return hash((self.id, self.num, self.code))

    def __eq__(self, cls):
        return isinstance(cls, type(self)) and (cls.id, cls.num, cls.code) == (self.id, self.num, self.code)


class ExchangeRate(NamedTuple):
    """Represents exchange rate for the currency on the date

    :param date: Date of the exchange rate.
    :param currency: Currency for which the rate is fetched.
    :param value: Official exchange rates on selected date against the ruble.
    :param par: Nominal exchange rate.
    :param rate: Reduced exchange rate rate = value / par.
    """

    date: dt.datetime
    currency: Currency
    name: str  # exists for backward compatibility.
    value: Decimal
    par: Decimal
    rate: Decimal

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
    def num(self):
        return self.currency.num

    @property
    def code(self):
        return self.currency.code


class ExchangeRates(WithRequests, FormatMixin):
    """Gets and stores exchange rates for different currencies for a selected date

    :param date_requested: The date on which the rates are requested.
    :type date_requested: date
    :param date_received: The date of the rates that was returned from the Central Bank of Russia.
    :type date_received: date
    :param dates_match: Returns whether the requested rate date and response rate date are the same.
    :type dates_match: bool
    :param rates: Dictionary of ExchangeRate parsed from the server.
    :type rates: Dict[Currency, ExchangeRate]
    :param length: Number of exchange rates.
    :type length: int
    :param currencies_lib: Library of currencies.
    :type currencies_lib: Currencies

    :Example:

    Creation:
        rates = ExchangeRates()
        rates = ExchangeRates(date(2021, 08, 24))
        rates = ExchangeRates(on_date=datetime(2021, 08, 24, 0, 0))
        rates = ExchangeRates(on_date='2021-08-24', locale_en=True)
    Receiving:
        By ISO 4217 currency alphabetic code: rates[AUD], rates[aud]
        By ISO 4217 currency numeric code: rates['036'], rates['36'], rates[36]
        By the code of the Central Bank of Russia: rates['R01010'], rates['rR01010']

    .. note:: The Central Bank of Russia does not change rates on weekends and holidays.
        The Sunday and Monday rates is set as equal as Saturday rate.
        The rates of holiday is set as equal on the last working day before the holidays.
    """

    def __init__(self, on_date: Union[str, dt.date, dt.datetime, None] = None, locale_en: bool = False):
        """
        :param on_date: Date to get exchange rates for.
        :type on_date: str, date, datetime, optional
        :param locale_en: If not set ExchangeRate.name will be provided in Russian, otherwise in English.
        :type locale_en: bool
        """
        self.currencies_lib = Currencies()
        self.length = 0

        if on_date:
            on_date = self._datetime_from_string(on_date)
        else:
            today = dt.date.today()
            on_date = dt.datetime(today.year, today.month, today.day)  # For backward compatibility, the time is 00:00

        self.date_requested = on_date

        raw_data = self._get_data(on_date, locale_en)
        date_received, rates = self._parse(raw_data, locale_en)

        self.date_received: dt.datetime = date_received
        self.rates: Dict[Currency, ExchangeRate] = rates
        self.dates_match: bool = (self.date_requested == self.date_received)

    def __getitem__(self, item: Union[str, int, Currency]) -> Optional[ExchangeRate]:
        """Implement dictionary lookup

        :param item: Bank of Russia code, numeric or alphabetic currency code according to ISO, Currency instance
        :type item: str, int, Currency
        :return: The ExchangeRate instance for the requested currency
        :rtype: ExchangeRate, optional
        """
        try:
            key: Optional[Currency] = self.currencies_lib[item]
        except (WrongArguments, CurrencyNotFound):
            return None  # return None, not an exception, is made for backward compatibility.

        try:
            return self.rates[key]
        except ExchangeRateNotFound:
            return None  # return None, not an exception, is made for backward compatibility.

    def __len__(self):
        return len(self.rates)

    @classmethod
    def _get_data(cls, on_date: dt.datetime, locale_en: bool) -> bytes:
        """Prepares parameters for the link and returns raw XML"""
        url = f"{URL_BASE}XML_daily{'_eng' if locale_en else ''}.asp"
        params = {
            'date_req': on_date.strftime('%d/%m/%Y')
        }

        response = cls._get_response(url=url, params=params)
        raw_data = response.content

        return raw_data

    def _parse(self, data: bytes, locale_en: bool) -> Tuple[dt.datetime, Dict[Currency, ExchangeRate]]:
        """Parse raw XML strings to the dict of BetaExchangeRates"""
        LOG.debug('Parsing data ...')

        xml = ElementTree.fromstring(data)

        date_received = dt.datetime.strptime(xml.attrib['Date'], '%d.%m.%Y')

        result = {}

        for child in xml:
            params = {}
            for param in child:
                params[param.tag] = param.text

            try:
                currency = self.currencies_lib[child.attrib['ID']]
            except CurrencyNotFound:
                # The request for old information may contain a currency
                # that has already been removed from the Currencies.
                # In this case, add a new currency to Currencies.
                currency = Currency(id=child.attrib['ID'],
                                    name_eng=params['Name'],
                                    name_ru=params['Name'],
                                    code=params['CharCode'],
                                    num=params['NumCode'],
                                    par=Decimal(params['Nominal']),
                                    )
                self.currencies_lib.add(currency)

            name = currency.name_eng if locale_en else currency.name_ru
            par = Decimal(params['Nominal'])
            value = Decimal(params['Value'].replace(',', '.'))

            result[currency] = ExchangeRate(
                date=date_received,
                currency=currency,
                name=name,
                value=value,
                par=par,
                rate=value / par,
            )

        LOG.debug(f"Parsed: {len(result)} currencies")

        return date_received, result

    def __str__(self):
        return f"ExchangeRates of {len(self.rates)} currencies from {self.date_requested}"


class Currencies(WithRequests, FormatMixin, metaclass=SingletonMeta):
    """Singleton class represents library of Currency

    :param update_date: Date of loading the latest information from www.cbr.ru
    :type update_date: dt.datetime
    :param currencies: Dict of Currency
    :type currencies: Dict[str, Currency]

    .. note:: currencies represents {Union[Currency.id, Currency.num, Currency.code]: Currency} dictobject.
    """

    def __init__(self):
        self.update_date = None
        self.currencies = None
        self.update()

    def __getitem__(self, value: Union[int, str]) -> Optional[Currency]:
        """Returns Currency by dictionary lookup, converting the argument to ISO format."""
        if not value:
            raise CurrencyNotFound(f'Currency "{value}" not found.')

        item = self._format_num_code(value)
        item = item.lower()

        try:
            currency = self.currencies[item]
        except KeyError:
            raise CurrencyNotFound()

        return currency

    def update(self):
        """Get and parse actual data from the www.cbr.ru."""
        raw_data = self._get_data()
        self.currencies = self._parse(raw_data)
        self.update_date = dt.datetime.now()

    def add(self, currency: Currency):
        """Add a new currency to the library or update an existing currency"""
        if isinstance(currency, Currency):
            self.currencies.update(self._make_currency_pack(currency))

    @classmethod
    def _get_data(cls) -> Tuple[bytes, bytes]:
        """Get XML byte string from www.cbr.ru for dayly and monthly update currencies."""
        url = f"{URL_BASE}XML_valFull.asp"

        LOG.debug(f'Getting update currencies from {url} ...')

        daily_update_response = cls._get_response(url)
        daily_update_data = daily_update_response.content

        monhtly_update_response = cls._get_response(url, params={'d': 1})
        monthly_update_data = monhtly_update_response.content

        return daily_update_data, monthly_update_data

    @staticmethod
    def _make_currency_pack(currency: Currency) -> Dict[str, Currency]:
        """Creates a dict of three elements from the currency with the keys: id, code and num if they exists"""
        pack = {}

        pack[currency.id.lower()] = currency
        # Data from the Bank of Russia contains replaced currencies that do not have ISO attributes.
        # So additional If-statements were added to exclude None from the 'codes'.
        if currency.code:
            pack[currency.code.lower()] = currency
        if currency.num:
            pack[currency.num] = currency

        return pack

    def _parse(self, data: Tuple[bytes, bytes]) -> Dict[str, Currency]:
        """Parse XML bytes strings from www.cbr.ru to dict of Currencies."""
        currencies = {}
        counter = 0

        LOG.debug('Parsing data ...')

        for sub_data in data:
            root = ElementTree.fromstring(sub_data)

            for child in root:
                props = {}
                for prop in child:
                    props[prop.tag] = prop.text

                currency = Currency(
                    id=child.attrib['ID'],
                    name_eng=props['EngName'],
                    name_ru=props['Name'],
                    code=props['ISO_Char_Code'],
                    # ISO numeric code like '036' is loaded like '36', so it needs format to ISO 4217,
                    # also data from the Bank of Russia contains replaced currencies that do not have ISO attributes.
                    # additional If-statement was added to exclude format None
                    num=self._format_num_code(_) if (_ := props['ISO_Num_Code']) else None,
                    par=Decimal(props['Nominal']),
                )

                counter += 1
                currencies.update(self._make_currency_pack(currency))

        LOG.debug(f"Parsed: {counter} currencies")
        return currencies

    def __str__(self):
        return f"Currencies. Update {self.update_date}"


class ExchangeRateDynamics(WithRequests, FormatMixin):
    """Receives and stores exchange rates for one currency over a period of time

    :param date_from: Start date of the period for the exchange rate dynamics.
    :type date_from: dt.datetime
    :param date_to: End date of the period for the exchange rate dynamics.
    :type date_to: dt.datetime
    :param currency: The currency for which the exchange rates were requested.
    :type currency: Currency
    :param rates: Dictionary of ExchangeRate parsed from the server.
    :type rates: Dict[datetime, ExchangeRate])
    :param length: Number of exchange rates.
    :type length: int
    :param currencies_lib: Library of currencies.
    :type currencies_lib: Currencies

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
                 date_from: Union[str, dt.date, dt.datetime, None] = None,
                 date_to: Union[str, dt.date, dt.datetime, None] = None,
                 *,
                 currency: Union[str, int, Currency],
                 ):
        """
        :param date_from: Date of the exchange rate or start date of the period for the exchange rate dynamics.
            Python date and datetime objects and ISO date '%Y-%m-%d' string are supported.
        :type date_from: date, str, optional
        :param date_to: End date of the period for the exchange rate dynamics.
            Python date and datetime objects and ISO date '%Y-%m-%d' string are supported.
        :type date_to: date, str, optional
        :param currency: Currency for which you need to know the rate.
            Strings like ISO numeric code, ISO code or code the Bank of Russia or Currency instance are supported.
        :type currency: int, str, Currency:

        .. note:: If all arguments are specified, get the rate dynamics between the passed dates.
            If currency and one date are passed, get the rate of the specified currency at the date.
            If only currency is passed, get the exchange rate for today.
        """
        self.currencies_lib = Currencies()
        self.length = 0

        self.date_from, self.date_to, self.currency = self._check_and_convert_args(date_from, date_to, currency)

        raw_data = self._get_data(self.currency)
        rates = self._parse(raw_data)

        self.rates = rates

    def __getitem__(self, item: Union[str, dt.date, dt.datetime]) -> ExchangeRate:
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

    def __len__(self):
        return len(self.rates)

    def _check_and_convert_args(self,
                                date_from: Union[str, dt.date, dt.datetime, None],
                                date_to: Union[str, dt.date, dt.datetime, None],
                                currency: Union[str, int, Currency]
                                ) -> Tuple[dt.datetime, dt.datetime, Currency]:
        """Checks arguments and converts them to proper formats from strings and integer"""
        date_from = self._datetime_from_string(date_from)
        date_to = self._datetime_from_string(date_to)

        if not currency:
            raise WrongArguments('You must specify a currency if you want to get a range of currency rates.')

        if not date_from and not date_to:  # if both dates are empty
            today = dt.date.today()
            date_from = date_to = dt.datetime(today.year, today.month, today.day)  # datetime for unification
        elif bool(date_from) ^ bool(date_to):  # if any of the dates, but not both (XOR)
            date_from = date_to = next(filter(lambda x: x, (date_from, date_to)))

        if date_to < date_from:
            raise WrongArguments('The end date of the period must be later than the start date.')

        if currency and not isinstance(currency, Currency):
            currency: Currency = self.currencies_lib[currency]

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

    def _parse(self, data: bytes) -> Dict[dt.datetime, ExchangeRate]:
        """Parse raw XML strings with rate dynamics to the dict of ExchangeRate"""
        LOG.debug('Parsing data ...')

        xml = ElementTree.fromstring(data)
        currency = self.currency

        result = {}

        for child in xml:
            params = {}
            for param in child:
                params[param.tag] = param.text

            date_received = dt.datetime.strptime(child.attrib['Date'], '%d.%m.%Y')
            par = Decimal(params['Nominal'])
            value = Decimal(params['Value'].replace(',', '.'))

            result[date_received] = ExchangeRate(
                currency=currency,
                name=currency.name_eng,
                date=date_received,
                par=par,
                value=value,
                rate=value / par,
            )

        LOG.debug(f"Parsed: {len(result)} days")

        return result

    def __str__(self):
        return f"{self.currency.code} ExchangeRateDynamics from {self.date_from} to {self.date_to}"
