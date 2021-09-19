from decimal import Decimal

from pycbrf import ExchangeRates


def test_rates():
    rates = ExchangeRates('2016-06-26', locale_en=True)

    assert str(rates.date_requested) == '2016-06-26 00:00:00'
    assert str(rates.date_received) == '2016-06-25 00:00:00'
    assert not rates.dates_match

    assert rates['dummy'] is None
    assert rates[''] is None
    assert rates[None] is None
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


def test_exchange_rates_extra():
    # test without date, for today
    rates = ExchangeRates()

    assert len(rates) > 0

    assert rates['eur'].id == 'R01239'
    assert rates['EUR'].name_ru == 'Евро'
    assert rates['R01239'].name_eng == 'Euro'
    assert rates['r01239'].num == '978'
    assert rates['978'].code == 'EUR'
    assert rates[978].par == Decimal(1)

    assert rates['usd'].currency.id == 'R01235'
    assert rates['USD'].currency.name_ru == 'Доллар США'
    assert rates['R01235'].currency.name_eng == 'US Dollar'
    assert rates['r01235'].currency.num == '840'
    assert rates['840'].currency.code == 'USD'
    assert rates[840].currency.par == Decimal(1)

    # test with a request date different from the response date
    rates = ExchangeRates('2021-08-22')
    assert len(rates) == 34

    assert str(rates.date_requested) == '2021-08-22 00:00:00'
    assert str(rates.date_received) == '2021-08-21 00:00:00'
    assert not rates.dates_match

    assert rates['cad'].currency.id == 'R01350'
    assert rates['CAD'].currency.name_ru == 'Канадский доллар'
    assert rates['R01350'].currency.name_eng == 'Canadian Dollar'
    assert rates['r01350'].currency.num == '124'
    assert rates['124'].currency.code == 'CAD'
    assert rates[124].currency.par == Decimal(1)
    assert rates['CAD'].value == Decimal('57.5885')
    assert rates['CAD'].rate == Decimal('57.5885')

    assert rates['usd'].id == 'R01235'
    assert rates['USD'].name_ru == 'Доллар США'
    assert rates['R01235'].name_eng == 'US Dollar'
    assert rates['r01235'].num == '840'
    assert rates['840'].code == 'USD'
    assert rates[840].par == Decimal(1)
    assert rates['USD'].value == Decimal('74.3640')
    assert rates['USD'].rate == Decimal('74.3640')

    # test with the request date matching the response date
    rates = ExchangeRates('2021-08-24')
    assert len(rates) == 34

    assert str(rates.date_requested) == '2021-08-24 00:00:00'
    assert str(rates.date_received) == '2021-08-24 00:00:00'
    assert rates.dates_match

    assert rates['kzt'].currency.id == 'R01335'
    assert rates['KZT'].currency.name_ru == 'Казахстанский тенге'
    assert rates['R01335'].currency.name_eng == 'Kazakhstan Tenge'
    assert rates['r01335'].currency.num == '398'
    assert rates['398'].currency.code == 'KZT'
    assert rates[398].currency.par == Decimal(100)
    assert rates['KZT'].value == Decimal('17.3926')
    assert rates['KZT'].rate == Decimal('0.173926')

    assert rates['mdl'].id == 'R01500'
    assert rates['MDL'].name_ru == 'Молдавский лей'
    assert rates['R01500'].name_eng == 'Moldova Lei'
    assert rates['r01500'].num == '498'
    assert rates['498'].code == 'MDL'
    assert rates[498].par == Decimal(10)
    assert rates['MDL'].value == Decimal('41.9277')
    assert rates['MDL'].rate == Decimal('4.19277')
