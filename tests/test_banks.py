# -*- encoding: utf8 -*-
from __future__ import unicode_literals
from os import path

import pytest

from pycbrf import Banks


@pytest.mark.xfail
def test_get_archive():
    assert Banks._get_data_swift()


@pytest.mark.parametrize('legacy', [True, False])
def test_banks(legacy, monkeypatch, read_fixture):

    @classmethod  # hack
    def get_archive(cls, url):
        if legacy:

            basename = path.basename(url)

            if basename == 'bik_swift-bik.zip':
                return read_fixture(basename)

            return read_fixture('bik_db_28062018.zip')

        return read_fixture('20201204ED01OSBR.zip')

    monkeypatch.setattr(Banks, '_get_archive', get_archive)

    banks = Banks('2018-06-29' if legacy else '2020-11-04')

    bank = banks['045004641']

    if legacy:
        assert bank.place == 'НОВОСИБИРСК'
        assert bank.place_type.shortname == 'Г'
        assert bank.region.name == 'НОВОСИБИРСКАЯ ОБЛАСТЬ'

    else:
        assert bank.place == 'Новосибирск'
        assert bank.place_type == 'г'
        assert bank.region_code == '50'

    try:
        bank = banks['SABRRUMMNH1']  # by swift bic
        assert bank.bic == '045004641'
        
    except KeyError:  # no swift data
        pass

    annotated = Banks.annotate([bank])[0]
    assert annotated['БИК'] == '045004641'
    assert 'vkey' not in annotated['Тип']

    # Test restrictions
    if not legacy:
        bank = banks['044525487']
        assert bank.restricted
        assert len(bank.restrictions) == 2

        annotated = Banks.annotate([bank])[0]
        assert annotated['Ограничения']
