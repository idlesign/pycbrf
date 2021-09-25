from datetime import datetime
from decimal import Decimal
from logging import getLogger
from typing import Dict, NamedTuple, Tuple, Union, Optional
from xml.etree import ElementTree

from .constants import URL_BASE, DAILY_CURRENCIES, MONTHLY_CURRENCIES
from ..exceptions import CurrencyNotFound
from ..utils import SingletonMeta, FormatMixin, WithRequests

LOG = getLogger(__name__)

TypeCurrencyIndex = Dict[str, 'Currency']


class Currency(NamedTuple):
    """Represents a foreign currency.

    .. code-block::

        Currency(
            id='R01010',
            name_ru='Австралийский доллар',
            name_eng='Australian Dollar',
            num='036',
            code='AUD',
            par=Decimal('1')
        )
    """

    id: str
    """Internal code of the Bank of Russia."""

    name_eng: str
    """Currency name in English."""

    name_ru: str
    """Currency name in Russian."""

    num: str
    """ISO 4217 currency numeric code."""

    code: str
    """ISO 4217 currency alphabetic code."""

    par: Decimal
    """Nominal exchange rate."""

    def __hash__(self):
        return hash((self.id, self.num, self.code))

    def __eq__(self, obj):
        return isinstance(obj, type(self)) and (obj.id, obj.num, obj.code) == (self.id, self.num, self.code)


class Currencies(WithRequests, FormatMixin, metaclass=SingletonMeta):
    """Represents known currencies data."""

    def __init__(self):
        self.updated: Optional[datetime] = None
        """Date of loading the latest information from www.cbr.ru"""

        self.currencies: TypeCurrencyIndex = self._parse((DAILY_CURRENCIES, MONTHLY_CURRENCIES))
        """Known currencies."""

    def __getitem__(self, value: Union[int, str]) -> Currency:
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
        self.updated = datetime.now()

    def register(self, currency: Currency):
        """Registers a currency. Can be used to update an existing currency data.

        :param currency:

        """
        self.currencies.update(self._index_currency(currency))

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
    def _index_currency(currency: Currency) -> TypeCurrencyIndex:
        """Creates a dict of three elements from the currency with the keys: id, code and num if they exists"""
        pack = {currency.id.lower(): currency}

        # Data from the Bank of Russia contains replaced currencies that do not have ISO attributes.
        # So additional If-statements were added to exclude None from the 'codes'.
        if currency.code:
            pack[currency.code.lower()] = currency

        if currency.num:
            pack[currency.num] = currency

        return pack

    def _parse(self, data: Tuple[bytes, bytes]) -> TypeCurrencyIndex:
        """Parse XML bytes strings from www.cbr.ru to dict of Currencies."""
        currencies = {}
        counter = 0

        LOG.debug('Parsing data ...')

        index = self._index_currency
        format_num = self._format_num_code

        for sub_data in data:
            root = ElementTree.fromstring(sub_data)

            for child in root:
                props = {}
                for prop in child:
                    props[prop.tag] = prop.text

                num = props['ISO_Num_Code'] or None
                if num:
                    # ISO numeric code like '036' is loaded like '36', so it needs to be formatted into ISO 4217,
                    # also data from the Bank of Russia contains replaced currencies that do not have ISO attributes.
                    # additional If-statement was added to exclude format None
                    num = format_num(num)

                currency = Currency(
                    id=child.attrib['ID'],
                    name_eng=props['EngName'],
                    name_ru=props['Name'],
                    code=props['ISO_Char_Code'],
                    num=num,
                    par=Decimal(props['Nominal']),
                )

                counter += 1
                currencies.update(index(currency))

        LOG.debug(f"Parsed: {counter} currencies")
        return currencies

    def __str__(self):
        return f"Currencies. Update {self.updated}"


CURRENCIES = Currencies()
