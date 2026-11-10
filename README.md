# pycbrf

<https://github.com/idlesign/pycbrf>

[![release](https://img.shields.io/pypi/v/pycbrf.svg)](https://pypi.python.org/pypi/pycbrf)
[![lic](https://img.shields.io/pypi/l/pycbrf.svg)](https://pypi.python.org/pypi/pycbrf)
[![coverage](https://img.shields.io/coveralls/idlesign/pycbrf/master.svg)](https://coveralls.io/r/idlesign/pycbrf)

## Description

*Tools to query Bank of Russia*

Provides methods to get the following information:

1. Exchange rates on various dates (including basic currencies data)
2. Banks information (requisites, codes, numbers, etc.)

## Requirements

* Python 3.10+
* `requests` Python package
* `dbf_light` Python package (to support legacy Bank format)
* `click` package (optional, for CLI)

## Usage

### CLI

```shell
$ pycbrf --help

$ pycbrf rates
$ pycbrf rates -d 2016-06-26 -c USD

$ pycbrf banks
$ pycbrf banks -b 045004641
```

CLI requires `click` package to be installed. Can be installed with `pycbrf` using:

```shell
$ pip install pycbrf[cli]
```

### Python

```python
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

banks = Banks()
bank = banks['045004641']
assert bank
bank.swift  # SABRRUMMNH1
bank.corr  # 30101810500000000641

bank_annotated = Banks.annotate([bank])[0]
for title, value in bank_annotated.items():
    print(f'{title}: {value}')
```
