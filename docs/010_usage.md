# Usage

## CLI

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

## Python

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
