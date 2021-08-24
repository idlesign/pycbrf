from datetime import datetime, date
from decimal import Decimal

import pytest

from pycbrf import ExchangeRates, CurrenciesLib, Currency, BetaExchangeRates
from pycbrf.exceptions import CurrencyNotExists, WrongArguments, ExchangeRateNotExists


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
    pre_date = datetime.now()
    lib = CurrenciesLib()
    aud = Currency(
        id='R01010',
        name_eng='Australian Dollar',
        name_ru='Австралийский доллар',
        num='036',
        code='AUD',
        nominal=Decimal(1)
    )

    assert len(lib) > 0
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
    assert lib[408].nominal == Decimal(100)

    fer = Currency(
        id='R99999',
        name_eng='Lunar ferting',
        name_ru='Лунный фертинг',
        num='999',
        code='FER',
        nominal=Decimal(1000)
    )
    lib.add(fer)

    assert lib['fer'].id == 'R99999'
    assert lib['FER'].name_ru == 'Лунный фертинг'
    assert lib['R99999'].name_eng == 'Lunar ferting'
    assert lib['r99999'].num == '999'
    assert lib['999'].code == 'FER'
    assert lib[999].nominal == Decimal(1000)

    post_date = datetime.now()
    assert lib.update_date < post_date

    lib.update()
    assert lib.update_date > post_date


def test_beta_exchange_rates_wrong_args():
    pytest.raises(WrongArguments, BetaExchangeRates, '2021-08-22', '2021-08-25')
    pytest.raises(WrongArguments, BetaExchangeRates, '2021-08-24', '2021-08-22')


def test_beta_multicurrencies_exchange_rates():
    # test without date, for today
    rates = BetaExchangeRates()

    assert len(rates) > 0

    with pytest.raises(CurrencyNotExists):
        result = rates['dummy']

    with pytest.raises(WrongArguments):
        result = rates['']

    with pytest.raises(WrongArguments):
        result = rates[None]

    with pytest.raises(ExchangeRateNotExists):
        result = rates['AOA']

    with pytest.raises(ExchangeRateNotExists):
        result = rates[971]

    assert rates['eur'].id == 'R01239'
    assert rates['EUR'].name_ru == 'Евро'
    assert rates['R01239'].name_eng == 'Euro'
    assert rates['r01239'].num == '978'
    assert rates['978'].code == 'EUR'
    assert rates[978].nominal == Decimal(1)

    assert rates['usd'].currency.id == 'R01235'
    assert rates['USD'].currency.name_ru == 'Доллар США'
    assert rates['R01235'].currency.name_eng == 'US Dollar'
    assert rates['r01235'].currency.num == '840'
    assert rates['840'].currency.code == 'USD'
    assert rates[840].currency.nominal == Decimal(1)

    # test with a request date different from the response date
    rates = BetaExchangeRates('2021-08-22')
    assert len(rates) == 34

    assert str(rates['EUR'].date_requested) == '2021-08-22'
    assert str(rates['EUR'].date_received) == '2021-08-21'
    assert not rates['EUR'].dates_match

    assert rates['cad'].currency.id == 'R01350'
    assert rates['CAD'].currency.name_ru == 'Канадский доллар'
    assert rates['R01350'].currency.name_eng == 'Canadian Dollar'
    assert rates['r01350'].currency.num == '124'
    assert rates['124'].currency.code == 'CAD'
    assert rates[124].currency.nominal == Decimal(1)

    assert rates['usd'].id == 'R01235'
    assert rates['USD'].name_ru == 'Доллар США'
    assert rates['R01235'].name_eng == 'US Dollar'
    assert rates['r01235'].num == '840'
    assert rates['840'].code == 'USD'
    assert rates[840].nominal == Decimal(1)

    # test with the request date matching the response date
    rates = BetaExchangeRates('2021-08-24')
    assert len(rates) == 34

    assert str(rates['DKK'].date_requested) == '2021-08-24'
    assert str(rates['DKK'].date_received) == '2021-08-24'
    assert rates['DKK'].dates_match

    assert rates['kzt'].currency.id == 'R01335'
    assert rates['KZT'].currency.name_ru == 'Казахстанский тенге'
    assert rates['R01335'].currency.name_eng == 'Kazakhstan Tenge'
    assert rates['r01335'].currency.num == '398'
    assert rates['398'].currency.code == 'KZT'
    assert rates[398].currency.nominal == Decimal(100)

    assert rates['MDL'].id == 'R01500'
    assert rates['MDL'].name_ru == 'Молдавский лей'
    assert rates['R01500'].name_eng == 'Moldova Lei'
    assert rates['r01500'].num == '498'
    assert rates['498'].code == 'MDL'
    assert rates[498].nominal == Decimal(10)

    # test with a very old date with a currency that is not in the CurrenciesLib
    lib = CurrenciesLib()
    with pytest.raises(CurrencyNotExists) as e:
        lib['BYR']
    assert e.value.message == 'There is no such currency within CurrenciesLib.'

    rates = BetaExchangeRates('2016-06-26')

    assert str(rates['BYR'].date_requested) == '2016-06-26'
    assert str(rates['BYR'].date_received) == '2016-06-25'
    assert not rates['BYR'].dates_match

    assert rates['BYR'].id == 'R01090'
    assert rates['byr'].name_ru == 'Белорусских рублей'
    assert rates['R01090'].name_eng == 'Белорусских рублей'
    assert rates['r01090'].num == '974'
    assert rates['974'].code == 'BYR'
    assert rates[974].nominal == Decimal(10000)


def test_beta_multidate_exchange_rates():
    # test with currency without dates, for today
    rates = BetaExchangeRates(currency='USD')

    assert rates.date_from == date.today()
    assert rates.date_from == date.today()
    assert not rates.is_multicurrency
    assert len(rates) in (0, 1)

    # test with specific date
    date_check = date(year=2021, month=8, day=24)
    rates = BetaExchangeRates(date_check, currency='EUR')

    assert len(rates) == 1
    assert rates[date_check].id == 'R01239'
    assert rates[datetime.now().date()].name_ru == 'Евро'
    assert rates['2021-08-24'].name_eng == 'Euro'
    assert rates['2021-08-24'].num == '978'
    assert rates['2021-08-24'].code == 'EUR'
    assert rates['2021-08-24'].nominal == Decimal(1)

    # test with a period of one day
    rates = BetaExchangeRates('2021-08-10', '2021-08-10', currency='R01215')
    date_check = date(2021, 8, 10)
    datetime_check = datetime(2021, 8, 10)

    assert len(rates) == 1
    assert rates['2021-08-10'].id == 'R01215'
    assert rates[date_check].name_ru == 'Датская крона'
    assert rates[datetime_check].name_eng == 'Danish Krone'
    assert rates['2021-08-10'].num == '208'
    assert rates['2021-08-10'].code == 'DKK'
    # this is represents problem of nominals between rate and currency
    assert rates['2021-08-10'].nominal == Decimal(1)
    assert rates['2021-08-10'].currency.nominal == Decimal(10)

    # test period of rates
    rates = BetaExchangeRates('2021-08-01', '2021-08-24', currency=203)

    assert len(rates) == 16
    assert rates['2021-08-10'].currency.id == 'R01760'
    assert rates[date_check].currency.name_ru == 'Чешская крона'
    assert rates[datetime_check].currency.name_eng == 'Czech Koruna'
    assert rates['2021-08-10'].currency.num == '203'
    assert rates['2021-08-10'].currency.code == 'CZK'
    assert rates['2021-08-10'].currency.nominal == Decimal(10)
    assert rates['2021-08-10'].nominal == Decimal(10)
    assert rates['2021-08-10'].value == Decimal('34.0109')
    assert rates['2021-08-10'].rate == Decimal('3.40109')

    # test with a date without rates
    rates = BetaExchangeRates('2021-08-01', '2021-08-24', currency='R01750')
    assert len(rates) == 0

    assert not len(rates)
    with pytest.raises(ExchangeRateNotExists) as e:
        assert rates[date.today()]
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'

    with pytest.raises(ExchangeRateNotExists) as e:
        assert rates['2021-08-23']
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'

    with pytest.raises(ExchangeRateNotExists) as e:
        assert rates['2021-08-24']
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'
