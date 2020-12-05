pycbrf
======
https://github.com/idlesign/pycbrf

.. image:: https://img.shields.io/pypi/v/pycbrf.svg
    :target: https://pypi.python.org/pypi/pycbrf

.. image:: https://img.shields.io/pypi/l/pycbrf.svg
    :target: https://pypi.python.org/pypi/pycbrf

.. image:: https://img.shields.io/coveralls/idlesign/pycbrf/master.svg
    :target: https://coveralls.io/r/idlesign/pycbrf

.. image:: https://img.shields.io/travis/idlesign/pycbrf/master.svg
    :target: https://travis-ci.org/idlesign/pycbrf


Description
-----------

*Tools to query Bank of Russia*

Provides methods to get the following information:

1. Exchange rates on various dates
2. Banks information (requisites, codes, numbers, etc.)


Requirements
------------

* Python 3.6+
* ``requests`` Python package
* ``dbf_light`` Python package (to support legacy Bank format)
* ``click`` package (optional, for CLI)


Usage
-----

CLI
~~~

.. code-block:: bash

    $ pycbrf --help

    $ pycbrf rates
    $ pycbrf rates -d 2016-06-26 -c USD

    $ pycbrf banks
    $ pycbrf banks -b 045004641


CLI requires ``click`` package to be installed. Can be installed with ``pycbrf`` using:

.. code-block:: bash

    $ pip install pycbrf[cli]



Python
~~~~~~

.. code-block:: python

    from pycbrf import ExchangeRates, Banks


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

    banks = Banks()
    bank = banks['045004641']
    assert bank
    bank.swift  # SABRRUMMNH1
    bank.corr  # 30101810500000000641

    bank_annotated = Banks.annotate([bank])[0]
    for title, value in bank_annotated.items():
        print(f'{title}: {value}')

