# -*- encoding: utf8 -*-
from __future__ import unicode_literals
from os import path

from pycbrf import Banks


def test_get_archive():
    assert Banks._get_data_swift()


def test_banks(monkeypatch, read_fixture):

    @classmethod  # hack
    def get_archive(cls, url):
        basename = path.basename(url)

        if basename == 'bik_swift-bik.zip':
            return read_fixture(basename)

        return read_fixture('bik_db_28062018.zip')

    monkeypatch.setattr(Banks, '_get_archive', get_archive)

    banks = Banks('2018-06-29')

    bank = banks['045004641']
    assert bank.place == 'НОВОСИБИРСК'
    assert bank.place_type.shortname == 'Г'
    assert bank.region.name == 'НОВОСИБИРСКАЯ ОБЛАСТЬ'

    bank = banks['SABRRUMMNH1']  # by swift bic
    assert bank.bic == '045004641'

    annotated = Banks.annotate([bank])[0]
    assert annotated['БИК'] == '045004641'
    assert 'vkey' not in annotated['Тип']
