from decimal import Decimal

from pycbrf import ExchangeRates, CurrenciesLib, Currency


def test_rates():
    rates = ExchangeRates('2016-06-26', locale_en=True)

    assert str(rates.date_requested) == '2016-06-26 00:00:00'
    assert str(rates.date_received) == '2016-06-25 00:00:00'
    assert not rates.dates_match

    assert rates['dummy'] is None
    assert rates['USD'].name == 'US Dollar'
    assert rates['R01235'].name == 'US Dollar'
    assert rates['840'].name == 'US Dollar'

    rates = ExchangeRates('2016-06-25')

    assert str(rates.date_requested) == '2016-06-25 00:00:00'
    assert str(rates.date_received) == '2016-06-25 00:00:00'
    assert rates.dates_match

    assert rates['USD'].name == 'Доллар США'
    assert rates['R01235'].name == 'Доллар США'
    assert rates['840'].name == 'Доллар США'


def test_currencieslib():
    lib = CurrenciesLib()
    aud = Currency(
        id='R01010',
        name_eng='Australian Dollar',
        name_ru='Австралийский доллар',
        num='036',
        code='AUD',
        par=Decimal(1)
    )

    assert lib['dummy'] is None
    assert lib['None'] is None
    assert lib[None] is None

    assert lib['aud'] == aud
    assert lib['AUD'] == aud
    assert lib['R01010'] == aud
    assert lib['r01010'] == aud
    assert lib['036'] == aud
    assert lib['36'] == aud
    assert lib[36] == aud

    assert lib['usd'].name_ru == 'Доллар США'
    assert lib['USD'].name_eng == 'US Dollar'
