from datetime import datetime, date
from decimal import Decimal
from logging import getLogger
from typing import Dict, List, NamedTuple, Optional, Tuple, Union, Type
from xml.etree import ElementTree

from .exceptions import WrongArguments, CurrencyNotExists, ExchangeRateNotExists
from .utils import SingletonMeta, WithRequests, FormatMixin

LOG = getLogger(__name__)
URL_BASE = 'http://www.cbr.ru/scripts/'


class Currency(NamedTuple):
    """Represents a foreign currency.

    Attributes: # noqa
        id (str): Internal code of the Bank of Russia.
        name_eng (str): Currency name in English.
        name_ru (str): Currency name in Russian.
        par (Decimal): Nominal exchange rate.
        num (str, optional): ISO 4217 currency numeric code.
        code (str, optional): ISO 4217 currency alphabetic code.

    Examples:
        Currency(
            id='R01010',
            name_ru='Австралийский доллар',
            name_eng='Australian Dollar',
            num='036',
            code='AUD',
            par=Decimal('1'))
    """

    id: str
    name_ru: str
    name_eng: str
    num: str
    code: str
    nominal: Decimal

    def __hash__(self):
        return hash((self.id, self.num, self.code))

    def __eq__(self, cls):
        return isinstance(cls, type(self)) and (cls.id, cls.num, cls.code) == (self.id, self.num, self.code)


class CurrenciesLib(WithRequests, FormatMixin, metaclass=SingletonMeta):
    """Singleton class represents library of Currency

    Attributes:
        length (int):
            the number of different currencies in the library
        update_date (date):
            date of loading the latest information from www.cbr.ru
        currencies (dict of Currency):
            a {Union[Currency.id, Currency.num, Currency.code]: Currency} dictionary for all currencies
    """

    def __init__(self):
        self.length = 0
        self.update_date = None
        self.currencies = None
        self.update()

    def update(self):
        """Get and parse actual data from the www.cbr.ru."""
        raw_data = self._get_data()
        self.currencies = self._parse(raw_data)
        self.update_date = datetime.now()

    def add(self, currency: Currency):
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
    def _make_currency_pack(currency):
        """Creates a dict of three elements from the currency with the keys: id, code and num if they exists"""
        pack = dict()

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
                    nominal=Decimal(props['Nominal']),
                )

                counter += 1
                currencies.update(self._make_currency_pack(currency))

        self.length = counter
        LOG.debug(f"Parsed: {self.length} currencies")
        return currencies

    def __getitem__(self, value: Union[int, str]) -> Optional[Currency]:
        """Returns Currency by dictionary lookup, converting the argument to ISO format."""
        if not value:
            raise WrongArguments(f"You must pass ISO code, numeric code or code the Bank of Russia of currency or "
                                 f"Currency instance. Not {'None' if value is None else 'empty string'}.")
        item_ = self._format_num_code(value)
        item_ = item_.lower()

        try:
            currency = self.currencies[item_]
        except KeyError:
            raise CurrencyNotExists()

        return currency

    def __str__(self):
        return f"CurrenciesLib of {self.length} currencies. Update {date.strftime(self.update_date, '%Y-%m-%d')}"

    def __len__(self):
        return self.length


class BetaExchangeRate(NamedTuple):
    """Rethinking ExchangeRate class
    Represents exchange rate for the currency on the date

    Attributes: # noqa
        curency (Currency):
            Currency for which the rate is fetched.
        date (datetime.date):
            Date of the exchange rate.
        nominal (Decimal):
            Nominal exchange rate
        value (Decimal):
            Official exchange rates on selected date against the ruble
        rate (Decimal):
            Reduced exchange rate
        dates_match (bool):
            Returns whether the requested rate date and response rate date are the same.
            Because the Central Bank of Russia does not change rates on weekends and holidays.
            The Sunday and Monday rates is set as equal as Saturday rate.
            The rates of holiday is set as equal on the last working day before the holidays.
    """
    currency: Currency
    date: datetime.date
    nominal: Decimal
    value: Decimal
    rate: Decimal
    date_requested: date
    date_received: date
    dates_match: Optional[bool]

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


class BetaExchangeRates(WithRequests, FormatMixin):
    """Rethinking ExchangeRates class
    Fetches and collect exchange rates.

    Attributes:
        date_from(str, datetime.date):
            Start date of the period for the exchange rate dynamics
        date_to(str, datetime.date):
            End date of the period for the exchange rate dynamics.
            Python date objects and ISO date '%Y-%m-%d' string are supported.
            If rates is requested in one day is equal to date_from
        is_multicurrency (bool):
            True if the collection contains multicurrency rates for a specific date.
            False if the collection contains rate dynamics for one currency.
        currencies_lib (CurrenciesLib):
            Library of currencies.
            Not passed, create during class initialization
    """

    def __init__(self,
                 date_from: Union[date, str, None] = None,
                 date_to: Union[date, str, None] = None,
                 *,
                 currency: Union[str, int, Currency] = None,
                 ):
        """
        Args:
            date_from:
                Date of the exchange rate or start date of the period for the exchange rate dynamics.
                Python date objects and ISO date '%Y-%m-%d' string are supported
            date_to:
                End date of the period for the exchange rate dynamics
                Python date objects and ISO date '%Y-%m-%d' string are supported
            currency:
                Currency for which you need to know the rate.
                Strings like ISO numeric code, ISO code or code the Bank of Russia or Currency instance are supported.

        """
        self.currencies_lib = CurrenciesLib()
        self.date_from, self.date_to, currency_ = self._check_and_convert_args(date_from, date_to, currency)

        if currency:
            self.is_multicurrency = False
            raw_data = self._get_rate_dynamics_data(currency_)
            self.rates = self._parse_rate_dynamics(raw_data)
        else:
            self.is_multicurrency = True
            raw_data = self._get_multicurrency_rates_data()
            self.rates = self._parse_multicurrency_rates(raw_data)

    def _check_and_convert_args(self, date_from, date_to, currency) -> Tuple[date, date, Currency]:
        """Checks arguments and converts them to proper formats from strings and integer"""

        date_from = self._date_from_string(date_from)
        date_to = self._date_from_string(date_to)

        if date_to and date_from and date_from != date_to and not currency:
            raise WrongArguments('You must specify a currency if you want to get a range of currency rates.')

        if not date_from and not date_to:  # if both dates are empty
            date_from = date_to = date.today()
        elif bool(date_from) ^ bool(date_to):  # if any of the dates, but not both (XOR)
            date_from = date_to = next(filter(lambda x: x, (date_from, date_to)))

        if date_to < date_from:
            raise WrongArguments('The end date of the period must be later than the start date.')

        if currency and not isinstance(currency, Currency):
            currency: Currency = self.currencies_lib[currency]

        return date_from, date_to, currency

    def _get_rate_dynamics_data(self, currency: Currency) -> bytes:
        """If the currency is passed, get a rate dynamics XML string for a specific currency.

        If all arguments are specified, get the course dynamics between the passed dates.
        If currency and one date are passed, get the rate of the specified currency at the date.
        If only currency is passed, get the exchange rate for today."""

        url_suffix = 'XML_dynamic'
        params = {
            'date_req1': self.date_from.strftime('%d/%m/%Y'),
            'date_req2': self.date_to.strftime('%d/%m/%Y'),
            'VAL_NM_RQ': currency.id,
        }

        raw_data = self._get_data(suffix=url_suffix, params=params)

        return raw_data

    def _get_multicurrency_rates_data(self) -> bytes:
        """If no currency is passed, get a multicurrency rates XML string for a specific date.

        If date_from or date_to are passed, get multicurrency rates on the specified date.
        If no date is passed, get the multicurrencies courcies for today.
        If date_from and date_to are passed, initiate checks.
        """

        url_suffix = 'XML_daily'
        params = {
            'date_req': self.date_from.strftime('%d/%m/%Y'),
        }

        raw_data = self._get_data(suffix=url_suffix, params=params)

        return raw_data

    @classmethod
    def _get_data(cls, suffix, params) -> bytes:
        """Returns XML string from link"""
        url = f"{URL_BASE}{suffix}.asp"

        LOG.debug(f'Getting exchange rates from {url} ...')

        response = cls._get_response(url, params=params)
        data = response.content

        return data

    def _parse_rate_dynamics(self, data) -> Dict[date, BetaExchangeRate]:
        """Parse raw XML strings with rate dynamics to the dict of BetaExchangeRates"""
        LOG.debug('Parsing rate dynamics data ...')

        xml = ElementTree.fromstring(data)
        currency = self.currencies_lib[xml.attrib['ID']]

        result = {}

        for child in xml:
            elems = {}
            for elem in child:
                elems[elem.tag] = elem.text

            date_received = datetime.strptime(child.attrib['Date'], '%d.%m.%Y').date()
            nominal = Decimal(elems['Nominal'])
            value = Decimal(elems['Value'].replace(',', '.'))

            result[date_received] = BetaExchangeRate(
                currency=currency,
                date=date_received,
                nominal=nominal,
                value=value,
                rate=value / nominal,
                date_requested=date_received,
                date_received=date_received,
                dates_match=True,
            )

        LOG.debug(f"Parsed: {len(result)} days")

        return result

    def _parse_multicurrency_rates(self, data) -> Dict[Currency, BetaExchangeRate]:
        """Parse raw XML strings with multicurrency reates to the dict of BetaExchangeRates"""
        LOG.debug('Parsing multicurrency reates data ...')

        xml = ElementTree.fromstring(data)

        date_requested = self.date_from
        date_received = datetime.strptime(xml.attrib['Date'], '%d.%m.%Y').date()
        dates_match = date_requested == date_received

        result = {}

        for child in xml:
            elems = {}
            for elem in child:
                elems[elem.tag] = elem.text

            try:
                currency = self.currencies_lib[child.attrib['ID']]
            except CurrencyNotExists:
                # If you are requesting really old information, the rates may contain a currency,
                # that has already been removed from the CurrenciesLib.
                # In this case, add the currency to the CurrenciesLib.
                currency = Currency(
                    id=child.attrib['ID'],
                    name_eng=elems['Name'],
                    name_ru=elems['Name'],
                    code=elems['CharCode'],
                    num=elems['NumCode'],
                    nominal=Decimal(elems['Nominal']),
                )
                self.currencies_lib.add(currency)

            nominal = Decimal(elems['Nominal'])
            value = Decimal(elems['Value'].replace(',', '.'))

            result[currency] = BetaExchangeRate(
                currency=currency,
                date=date_received,
                nominal=nominal,
                value=value,
                rate=value / nominal,
                date_requested=date_requested,
                date_received=date_received,
                dates_match=dates_match,
            )

            LOG.debug(f"Parsed: {len(result)} currencies")

        return result

    def __getitem__(self, value: Union[Currency, date, str, int]) -> BetaExchangeRate:
        """Returns the ExchangeRate by date or by currency depending on the ExchangeRates type.
        If ExchangeRates is multicurrency find by id, num and code params of Currency, or Currency class.
        If ExchangeRates is multidate find by date objects or '%Y-%m-%d' ISO date string
        """
        if not value:
            raise WrongArguments(f"Args must be ISO code, numeric code, code the Bank of Russia of currency, "
                                 f"Currency instance, datetime.date or  or '%Y-%m-%d' ISO date string."
                                 f"Not {'None' if value is None else 'empty string'}.")

        if self.is_multicurrency:
            key_str = self._format_num_code(value)
            key = self.currencies_lib[key_str]
        else:
            if isinstance(value, datetime):
                key = value.date()
            else:
                key = self._date_from_string(value)

        try:
            return self.rates[key]
        except KeyError:
            raise ExchangeRateNotExists()

    def __len__(self):
        return len(self.rates)

    def __str__(self):
        return f"{'MulticurrencyExchangeRates' if self.is_multicurrency else 'MultidatesExchangeRates'} " \
               f"of {len(self.rates)} rates"


class ExchangeRate(NamedTuple):
    """Represents an exchange rate for a currency.

    Such objects will populate ExchangeRates().rates

    """
    id: str
    name: str
    code: str
    num: str
    value: Decimal
    par: Decimal
    rate: Decimal


class ExchangeRates(WithRequests):

    def __init__(self, on_date: Union[datetime, str] = None, locale_en: bool = False):
        """Fetches exchange rates.

        rates = ExchangeRates('2016-06-26', locale_en=True)

        Various indexing is supported:

        rates['USD']  # By ISO alpha code
        rates['R01235']  # By internal Bank of Russia code
        rates['840']  # By ISO numeric code.

        :param on_date: Date to get rates for.
            Python date objects and ISO date string are supported.
            If not set rates on latest available date will be returned (usually tomorrow).

        :param locale_en: Flag to get currency names in English.
            If not set names will be provided in Russian.

        """
        if isinstance(on_date, str):
            on_date = datetime.strptime(on_date, '%Y-%m-%d')

        self.dates_match: bool = False
        """
        Flag indicating whether rates were returned on exact same date as requested.
        Note that Bank of Russia won't issue different rates for every day of weekend.

        """

        raw_data = self._get_data(on_date, locale_en)
        parsed = self._parse(raw_data)

        self.date_requested = on_date
        """Date requested by user."""

        self.date_received: datetime = parsed['date']
        """Date returned by Bank of Russia."""

        if on_date is None:
            self.date_requested = self.date_received

        self.rates: List['ExchangeRate'] = parsed['rates']
        """Rates fetched from server as a list."""

        self.dates_match: bool = (self.date_requested == self.date_received)

    def __getitem__(self, item: str) -> Optional['ExchangeRate']:

        if item.isdigit():
            key = 'num'

        elif item.isalpha():
            key = 'code'

        else:
            key = 'id'

        indexed = {getattr(currency, key): currency for currency in self.rates}

        return indexed.get(item)

    @staticmethod
    def _parse(data):
        LOG.debug('Parsing data ...')

        xml = ElementTree.fromstring(data)
        meta = xml.attrib

        result = {
            'date': datetime.strptime(meta['Date'], '%d.%m.%Y'),
            'rates': [],
        }

        for currency in xml:
            props = {}
            for prop in currency:
                props[prop.tag] = prop.text

            par = Decimal(props['Nominal'])
            par_value = Decimal(props['Value'].replace(',', '.'))

            result['rates'].append(ExchangeRate(
                id=currency.attrib['ID'],
                name=props['Name'],
                code=props['CharCode'],
                num=props['NumCode'],
                value=par_value,
                par=par,
                rate=par_value / par,
            ))

        LOG.debug(f"Parsed: {len(result['rates'])} currencies")

        return result

    @classmethod
    def _get_data(cls, on_date: datetime = None, locale_en: bool = False) -> bytes:

        url = f"{URL_BASE}XML_daily{'_eng' if locale_en else ''}.asp"

        if on_date:
            url = f"{url}?date_req={on_date.strftime('%d/%m/%Y')}"

        LOG.debug(f'Getting exchange rates from {url} ...')

        response = cls._get_response(url)
        data = response.content

        return data
