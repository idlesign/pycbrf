# -*- encoding: utf8 -*-
from __future__ import division
from collections import namedtuple
from xml.etree import ElementTree
from logging import getLogger
from datetime import datetime
from decimal import Decimal

try:
    from urllib.request import urlopen

except ImportError:  # Py2
    from urllib2 import urlopen


LOG = getLogger(__name__)
URL_BASE = 'http://www.cbr.ru/scripts/'


ExchangeRate = namedtuple(
    'ExchangeRate',
    ['id', 'name', 'code', 'num', 'value', 'par', 'rate']
)
"""Represents an exchange rate for a currency.

Such objects will populate ExchangeRates().rates

"""


class ExchangeRates(object):

    def __init__(self, on_date=None, locale_en=False):
        """Fetches exchange rates.

        rates = ExchangeRates('2016-06-26', locale_en=True)

        Various indexing is supported:

        rates['USD']  # By ISO alpha code
        rates['R01235']  # By internal Bank of Russia code
        rates['840']  # By ISO numeric code.

        :param datetime|str on_date: Date to get rates for.
            Python date objects and ISO date string are supported.
            If not set rates on latest available date will be returned (usually tomorrow).

        :param bool locale_en: Flag to get currency names in English.
            If not set names will be provided in Russian.

        """
        if isinstance(on_date, str):
            on_date = datetime.strptime(on_date, '%Y-%m-%d')

        self.dates_match = False
        """
        Flag indicating whether rates were returned on exact same date as requested.
        Note that Bank of Russia won't issue different rates for every day of weekend.

        :type: bool
        """

        raw_data = self._get_data(on_date, locale_en)
        parsed = self._parse(raw_data)

        self.date_requested = on_date
        """Date request by user.

        :type: datetime
        """
        self.date_received = parsed['date']
        """Date returned by Bank of Russia.

        :type: datetime
        """

        if on_date is None:
            self.date_requested = self.date_received

        self.rates = parsed['rates']
        """Rates fetched from server as a list.

        :type: list[ExchangeRate]
        """

        self.dates_match = (self.date_requested == self.date_received)

    def __getitem__(self, item):
        """
        :param str item:
        :rtype: ExchangeRate
        """
        if item.isdigit():
            key = 'num'
        elif item.isalpha():
            key = 'code'
        else:
            key = 'id'

        indexed = {getattr(currency, key): currency for currency in self.rates}

        return indexed[item]

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

            result['rates'].append(ExchangeRate(**{
                'id': currency.attrib['ID'],
                'name': props['Name'],
                'code': props['CharCode'],
                'num': props['NumCode'],
                'value': par_value,
                'par': par,
                'rate': par_value / par,
            }))

        LOG.debug('Parsed: %d currencies' % len(result['rates']))

        return result

    @staticmethod
    def _get_data(on_date=None, locale_en=False):

        url = URL_BASE + 'XML_daily%s.asp' % ('_eng' if locale_en else '')

        if on_date:
            url += '?date_req=%s' % on_date.strftime('%d/%m/%Y')

        LOG.debug('Getting exchange rates from %s ...' % url)

        response = urlopen(url)
        data = response.read()

        return data
