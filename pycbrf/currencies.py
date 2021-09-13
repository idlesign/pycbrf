import datetime as dt
from decimal import Decimal
from logging import getLogger
from typing import Dict, NamedTuple, Optional, Tuple, Union
from xml.etree import ElementTree

from .constants import URL_BASE, DAILY_CURRENCIES, MONTHLY_CURRENCIES
from .exceptions import CurrencyNotFound
from .utils import SingletonMeta, FormatMixin, WithRequests

LOG = getLogger(__name__)


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


class Currencies(WithRequests, FormatMixin, metaclass=SingletonMeta):
    """Singleton class represents library of Currency

    :param update_date: Date of loading the latest information from www.cbr.ru
    :param currencies: Dict of Currency

    .. note:: currencies represents {Union[Currency.id, Currency.num, Currency.code]: Currency} dict object.
    """

    def __init__(self):
        self.update_date = None
        self.currencies = self._parse((DAILY_CURRENCIES, MONTHLY_CURRENCIES))

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
        self.currencies.update(self._parse(raw_data))
        self.update_date = dt.datetime.now()

    def add(self, currency: Currency):
        """Add a new currency to the library or update an existing currency"""
        if isinstance(currency, Currency):
            self.currencies.update(self._make_currency_pack(currency))

    @classmethod
    def _get_data(cls) -> Tuple[bytes, bytes]:
        """Get XML byte string from www.cbr.ru for daily and monthly update currencies."""
        url = f"{URL_BASE}XML_valFull.asp"

        LOG.debug(f'Getting update currencies from {url} ...')

        daily_update_response = cls._get_response(url)
        daily_update_data = daily_update_response.content

        monthly_update_response = cls._get_response(url, params={'d': 1})
        monthly_update_data = monthly_update_response.content

        return daily_update_data, monthly_update_data

    @staticmethod
    def _make_currency_pack(currency: Currency) -> Dict[str, Currency]:
        """Creates a dict of three elements from the currency with the keys: id, code and num if they exists"""
        pack = {currency.id.lower(): currency}

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
