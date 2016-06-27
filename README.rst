pycbrf
======
https://github.com/idlesign/pycbrf

.. image:: https://img.shields.io/pypi/v/pycbrf.svg
    :target: https://pypi.python.org/pypi/pycbrf

.. image:: https://img.shields.io/pypi/dm/pycbrf.svg
    :target: https://pypi.python.org/pypi/pycbrf

.. image:: https://img.shields.io/pypi/l/pycbrf.svg
    :target: https://pypi.python.org/pypi/pycbrf

.. image:: https://img.shields.io/coveralls/idlesign/pycbrf/master.svg
    :target: https://coveralls.io/r/idlesign/pycbrf

.. image:: https://img.shields.io/travis/idlesign/pycbrf/master.svg
    :target: https://travis-ci.org/idlesign/dpycbrf

.. image:: https://landscape.io/github/idlesign/pycbrf/master/landscape.svg?style=flat
   :target: https://landscape.io/github/idlesign/pycbrf/master


Description
-----------

*Tools to query Bank of Russia*

Provides methods to get the following information:

1. Exchange rates on various dates


Requirements
------------

* Python 2.7, 3.2+


Getting Exchange Rates
----------------------

From command line:

.. code-block::

    $ pycbrf rates
    $ pycbrf rates -d 2016-06-26 -c USD


From your application:

.. code-block:: python

    from pycbrf.toolbox import ExchangeRates


    rates = ExchangeRates('2016-06-26', locale_en=True)

    rates.date_requested  # 2016-06-26 00:00:00
    rates.date_received  # 2016-06-25 00:00:00
    rates.dates_match  # False
    # Note: 26th of June was a holiday, data is taken from the 25th.

    # Various indexing is supported:
    rates['USD'].name  # US Dollar
    rates['R01235'].name  # US Dollar
    rates['840'].name  # US Dollar

    rates['USD']
    '''
        ExchangeRate(
            id='R01235',
            name='US Dollar',
            code='USD',
            num='840',
            value=Decimal('65.5287'),
            par=Decimal('1'),
            rate=Decimal('65.5287'))
    '''

