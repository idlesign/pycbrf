import datetime as dt
from decimal import Decimal

import pytest

from pycbrf import ExchangeRateDynamics
from pycbrf.exceptions import WrongArguments, ExchangeRateNotFound

today = dt.datetime.combine(dt.date.today(), dt.time())


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

    assert rates.since == today
    assert rates.since == today
    assert len(rates) in (0, 1)

    # test with specific date
    date_check = dt.datetime(year=2021, month=8, day=24)
    rates = ExchangeRateDynamics(date_check, currency='EUR')

    assert len(rates) == 1
    assert rates[date_check].id == 'R01239'
    assert rates[date_check.date()].name == 'Евро'
    assert rates['2021-08-24'].currency.name_eng == 'Euro'
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
    assert rates[date_check].name == 'Датская крона'
    assert rates[datetime_check].currency.name_eng == 'Danish Krone'
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
    with pytest.raises(ExchangeRateNotFound) as e:
        assert rates[today]
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'

    with pytest.raises(ExchangeRateNotFound) as e:
        assert rates['2021-08-23']
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'

    with pytest.raises(ExchangeRateNotFound) as e:
        assert rates['2021-08-24']
    assert e.value.message == 'There is no such ExchangeRate within ExchangeRates.'
