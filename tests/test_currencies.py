import datetime as dt
from decimal import Decimal

import pytest

from pycbrf import ExchangeRates, Currencies, Currency
from pycbrf.exceptions import CurrencyNotFound

today = dt.datetime.combine(dt.date.today(), dt.time())


def test_currencies():
    lib = Currencies()
    aud = Currency(
        id='R01010',
        name_eng='Australian Dollar',
        name_ru='Австралийский доллар',
        num='036',
        code='AUD',
        par=Decimal(1)
    )

    assert lib.update_date is None

    with pytest.raises(CurrencyNotFound) as e:
        lib[None]
    assert e.value.message == 'Currency "None" not found.'

    with pytest.raises(CurrencyNotFound) as e:
        lib['']
    assert e.value.message == 'Currency "" not found.'

    with pytest.raises(CurrencyNotFound) as e:
        lib['dummy']
    assert e.value.message == 'There is no such currency within Currencies.'

    with pytest.raises(CurrencyNotFound) as e:
        lib['None']
    assert e.value.message == 'There is no such currency within Currencies.'

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
    lib.update()
    post_date = dt.datetime.now()
    assert lib.update_date < post_date

    lib.update()
    assert lib.update_date > post_date

    # test with a very old date with a currency that is not in the Currencies
    # added by ExchangeRates automatically

    """Raising exceptions is disabled for backward compatibility."""
    with pytest.raises(CurrencyNotFound) as e:
        lib['BYR']
    assert e.value.message == 'There is no such currency within Currencies.'

    rates = ExchangeRates('2016-06-26', locale_en=True)

    assert rates['BYR'].id == 'R01090'
    assert rates['byr'].name_ru == 'Belarussian Ruble'
    assert rates['R01090'].name_eng == 'Belarussian Ruble'
    assert rates['r01090'].num == '974'
    assert rates['974'].code == 'BYR'
    assert rates[974].par == Decimal(10000)
    assert rates['BYR'].value == Decimal('32.6582')
    assert rates['BYR'].rate == Decimal('0.00326582')
