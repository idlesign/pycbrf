from datetime import datetime
from decimal import Decimal
from logging import getLogger
from typing import Dict, List, NamedTuple, Optional, Tuple, Union
from xml.etree import ElementTree

from .utils import SingletonMeta, WithRequests

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
    par: Decimal

    def __hash__(self):
        return hash((self.id, self.num, self.code))

    def __eq__(self, cls):
        return isinstance(cls, type(self)) and (cls.id, cls.num, cls.code) == (self.id, self.num, self.code)


class CurrenciesLib(WithRequests, metaclass=SingletonMeta):
    """Singleton class represents library of Currency

    Attributes:
        length (int): the number of different currencies in the library
        update_date (datetime): date of loading the latest information from www.cbr.ru
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

    def _parse(self, data: Tuple[bytes, bytes]) -> Dict[str, 'Currency']:
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
                    num=self.format_num_code(_) if (_ := props['ISO_Num_Code']) else None,
                    par=Decimal(props['Nominal']),
                )

                counter += 1
                currencies[currency.id.lower()] = currency
                # Data from the Bank of Russia contains replaced currencies that do not have ISO attributes.
                # So additional If-statements were added to exclude None from the 'codes'.
                if currency.code:
                    currencies[currency.code.lower()] = currency
                if currency.num:
                    currencies[currency.num] = currency

        self.length = counter
        LOG.debug(f"Parsed: {self.length} currencies")
        return currencies

    @staticmethod
    def format_num_code(num: Union[int, str]):
        """Format integer or invalid string numeric code to ISO 4217 currency numeric code."""
        num_ = num
        if isinstance(num_, str):
            num_ = int(num_)
        return "{:03}".format(num_)

    def __getitem__(self, item: Union[int, str]) -> Optional['Currency']:
        """Returns Currency by dictionary lookup, converting the argument to ISO format."""
        item_ = item
        if not item:
            return None
        if isinstance(item_, int) or (isinstance(item_, str) and len(item_) < 3):
            item_ = self.format_num_code(item_)
        item_ = item_.lower()

        return self.currencies.get(item_.lower())

    def __str__(self):
        return f"CurrenciesLib. {self.length} currencies. Update {datetime.strftime(self.update_date, '%Y-%m-%d')}"

    def __len__(self):
        return self.length


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
