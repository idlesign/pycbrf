import datetime as dt
from decimal import Decimal

import pytest

from pycbrf import ExchangeRates, CurrenciesLib, Currency, ExchangeRateDynamics
from pycbrf.exceptions import WrongArguments, CurrencyNotExists, ExchangeRateNotExists

today = dt.datetime.combine(dt.date.today(), dt.time())

def test_currencieslib():
    pre_date = dt.datetime.now()
    lib = CurrenciesLib()
    aud = Currency(
        id='R01010',
        name_eng='Australian Dollar',
        name_ru='Австралийский доллар',
        num='036',
        code='AUD',
        par=Decimal(1)
    )

    assert lib.update_date > pre_date

    with pytest.raises(WrongArguments) as e:
        lib[None]
    assert e.value.message == 'You must pass ISO code, numeric code or code the Bank of Russia of currency' \
                              ' or Currency instance. Not None.'

    with pytest.raises(WrongArguments) as e:
        lib['']
    assert e.value.message == 'You must pass ISO code, numeric code or code the Bank of Russia of currency' \
                              ' or Currency instance. Not empty string.'

    with pytest.raises(CurrencyNotExists) as e:
        lib['dummy']
    assert e.value.message == 'There is no such currency within CurrenciesLib.'

    with pytest.raises(CurrencyNotExists) as e:
        lib['None']
    assert e.value.message == 'There is no such currency within CurrenciesLib.'

    assert lib['aud'] == aud
    assert lib['AUD'] == aud
    assert lib['R01010'] == aud
    assert lib['r01010'] == aud
    assert lib['036'] == aud
    assert lib['36'] == aud
    assert lib[36] == aud

    assert lib['kpw'].id == 'R01145'
    assert lib['KPW'].name_ru == 'Вона КНДР'
    assert lib['R01145'].name_eng == 'North Korean Won'
    assert lib['r01145'].num == '408'
    assert lib['408'].code == 'KPW'
    assert lib[408].par == Decimal(100)

    """test to add a new Currency to the Library"""
    fer = Currency(
        id='R99999',
        name_eng='Lunar ferting',
        name_ru='Лунный фертинг',
        num='999',
        code='FER',
        par=Decimal(1000)
    )
    lib.add(fer)

    assert lib['fer'].id == 'R99999'
    assert lib['FER'].name_ru == 'Лунный фертинг'
    assert lib['R99999'].name_eng == 'Lunar ferting'
    assert lib['r99999'].num == '999'
    assert lib['999'].code == 'FER'
    assert lib[999].par == Decimal(1000)

    """test to CurrenicesLib.update()"""
    post_date = dt.datetime.now()
    assert lib.update_date < post_date

    lib.update()
    assert lib.update_date > post_date

    # test with a very old date with a currency that is not in the CurrenciesLib
    # added by ExchangeRates automatically

    """Raising exceptions is disabled for backward compatibility."""
    with pytest.raises(CurrencyNotExists) as e:
        lib['BYR']
    assert e.value.message == 'There is no such currency within CurrenciesLib.'

    rates = ExchangeRates('2016-06-26', locale_en=True)

    assert rates['BYR'].id == 'R01090'
    assert rates['byr'].name_ru == 'Belarussian Ruble'
    assert rates['R01090'].name_eng == 'Belarussian Ruble'
    assert rates['r01090'].num == '974'
    assert rates['974'].code == 'BYR'
    assert rates[974].par == Decimal(10000)
    assert rates['BYR'].value == Decimal('32.6582')
    assert rates['BYR'].rate == Decimal('0.00326582')


def test_rates():
    rates = ExchangeRates('2016-06-26', locale_en=True)

    # returns None for backward compatibility
    assert rates['dummy'] is None
    assert rates[''] is None
    assert rates[None] is None

    """Raising exceptions is disabled for backward compatibility."""
    # with pytest.raises(CurrencyNotExists) as e:
    #     rates['dummy']
    # assert e.value.message == 'There is no such currency within CurrenciesLib.'
    #
    # with pytest.raises(WrongArguments) as e:
    #     rates['']
    # assert e.value.message == "Args must be ISO code, numeric code, code the Bank of Russia of currency, " \
    #                           "Currency instance, datetime.date or  or '%Y-%m-%d' ISO date string.Not empty string."
    #
    # with pytest.raises(WrongArguments) as e:
    #     rates[None]
    # assert e.value.message == "Args must be ISO code, numeric code, code the Bank of Russia of currency, " \
    #                           "Currency instance, datetime.date or  or '%Y-%m-%d' ISO date string.Not None."
    #
    # with pytest.raises(ExchangeRateNotExists) as e:
    #     rates['AOA']
    # assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'
    #
    # with pytest.raises(ExchangeRateNotExists) as e:
    #     rates[971]
    # assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'

    assert str(rates.date_requested) == '2016-06-26 00:00:00'
    assert str(rates.date_received) == '2016-06-25 00:00:00'
    assert not rates.dates_match

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


def test_exchange_rate_dynamics_wrong_args():
    # dates of period without a currency
    pytest.raises(TypeError, ExchangeRateDynamics, '2021-08-22', '2021-08-25')
    # start date is later than end date
    pytest.raises(WrongArguments, ExchangeRateDynamics, '2021-08-24', '2021-08-22', currency='USD')
    # currency is empty string
    pytest.raises(WrongArguments, ExchangeRateDynamics, '2021-08-24', '2021-08-22', currency='')
    # currency is None
    pytest.raises(WrongArguments, ExchangeRateDynamics, '2021-08-24', '2021-08-22', currency=None)


def test_exchange_rate_dynamics():
    # test with currency without dates, for today
    rates = ExchangeRateDynamics(currency='USD')

    assert rates.date_from == today
    assert rates.date_from == today
    assert len(rates) in (0, 1)

    # test with specific date
    date_check = dt.datetime(year=2021, month=8, day=24)
    rates = ExchangeRateDynamics(date_check, currency='EUR')

    assert len(rates) == 1
    assert rates[date_check].id == 'R01239'
    assert rates[date_check.date()].name_ru == 'Евро'
    assert rates['2021-08-24'].name_eng == 'Euro'
    assert rates['2021-08-24'].num == '978'
    assert rates['2021-08-24'].code == 'EUR'
    assert rates['2021-08-24'].par == Decimal(1)
    assert rates['2021-08-24'].value == Decimal('86.7838')
    assert rates['2021-08-24'].rate == Decimal('86.7838')

    # test with a period of one day
    rates = ExchangeRateDynamics('2021-08-10', '2021-08-10', currency='R01215')
    date_check = dt.datetime(2021, 8, 10)
    datetime_check = dt.datetime(2021, 8, 10)

    assert len(rates) == 1
    assert rates['2021-08-10'].id == 'R01215'
    assert rates[date_check].name_ru == 'Датская крона'
    assert rates[datetime_check].name_eng == 'Danish Krone'
    assert rates['2021-08-10'].num == '208'
    assert rates['2021-08-10'].code == 'DKK'
    assert rates['2021-08-10'].par == Decimal(1)
    assert rates['2021-08-10'].value == Decimal('11.6245')
    assert rates['2021-08-10'].rate == Decimal('11.6245')

    # this is represents problem of nominals between rate and currency
    # That is the problem of the Bank of Russia library.
    # It does not affect the rate, just need to know about it
    assert rates['2021-08-10'].currency.par == Decimal(10)

    # test period of rates
    rates = ExchangeRateDynamics('2021-08-01', '2021-08-24', currency=203)

    assert len(rates) == 16
    assert rates['2021-08-10'].currency.id == 'R01760'
    assert rates[date_check].currency.name_ru == 'Чешская крона'
    assert rates[datetime_check].currency.name_eng == 'Czech Koruna'
    assert rates['2021-08-10'].currency.num == '203'
    assert rates['2021-08-10'].currency.code == 'CZK'
    assert rates['2021-08-10'].currency.par == Decimal(10)
    assert rates['2021-08-10'].par == Decimal(10)
    assert rates['2021-08-10'].value == Decimal('34.0109')
    assert rates['2021-08-10'].rate == Decimal('3.40109')

    # test with a date without rates
    rates = ExchangeRateDynamics('2021-08-01', '2021-08-24', currency='R01750')
    assert len(rates) == 0

    assert not len(rates)
    with pytest.raises(ExchangeRateNotExists) as e:
        assert rates[today]
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'

    with pytest.raises(ExchangeRateNotExists) as e:
        assert rates['2021-08-23']
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'

    with pytest.raises(ExchangeRateNotExists) as e:
        assert rates['2021-08-24']
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'
