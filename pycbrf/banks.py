# -*- encoding: utf8 -*-
from __future__ import unicode_literals

import re
from collections import namedtuple, OrderedDict
from datetime import datetime
from logging import getLogger
from xml.etree import ElementTree
from zipfile import ZipFile

from dbf_light import Dbf

from .exceptions import PycbrfException
from .utils import string_types, BytesIO, WithRequests, text_type

LOG = getLogger(__name__)


BankLegacy = namedtuple(
    'BankLegacy',
    [
        'bic',
        'name',
        'name_full',
        'region_code',
        'region',
        'zip',
        'place_type',
        'place',
        'address',
        'rkc_bic',
        'term',
        'date_added',
        'date_updated',
        'date_change',
        'mfo',
        'corr',
        'corr_bik',
        'phone',
        'telegraph',
        'commutator',
        'okpo',
        'regnum',
        'type',
        'pay_type',
        'control_code',
        'control_date',
        'swift',
    ]
)
"""Represents bank entry in legacy format.

Such objects will populate Banks().banks

"""

Bank = namedtuple(
    'Bank',
    [
        'bic',
        'name_full',
        'name_full_eng',
        'region_code',
        'country_code',
        'zip',
        'place_type',
        'place',
        'address',
        'date_added',
        'corr',
        'regnum',
        'type',
        'swift',
        'restricted',
        'restrictions',
    ]
)
"""Represents bank entry in current format.

Such objects will populate Banks().banks

"""


class Restriction(object):
    """Represents a restriction imposed on an institution."""

    __slots__ = ['code', 'date', 'account', 'title']

    codes = {
        'URRS': 'Ограничение предоставления сервиса срочного перевода',
        'LWRS': 'Отзыв (аннулирование) лицензии',
        'MRTR': 'Мораторий на удовлетворение требований кредиторов',
        'LMRS': 'Временное сохранение счета с его функционированием в ограниченном режиме',
        'CLRS': 'Закрытие счета',
        'FPRS': 'Приостановление предоставления сервиса быстрых платежей',
    }
    """УФЭБС_2021_1_1_КБР_Кодовые_Значения.pdf
    81 Статус участника
    82 Ограничения операций по счету

    """

    def __init__(self, code, date, account=''):
        self.code = code

        self.date = date

        self.account = account
        """Might be empty in not an account level restriction."""

        self.title = self.codes.get(code, '')

    def __str__(self):
        return '%s %s [%s] %s' % (
            self.date, self.code, self.account, self.title,
        )


class Banks(WithRequests):

    def __init__(self, on_date=None):
        """Fetches BIC data.

        :param datetime|str on_date: Date to get data for.
            Python date objects and ISO date string are supported.
            If not set data for today will be fetched.

        """
        if isinstance(on_date, string_types):
            on_date = datetime.strptime(on_date, '%Y-%m-%d')

        on_date = on_date or datetime.now()
        legacy = on_date < datetime(2018, 7, 1)

        self.banks = self._get_data(on_date=on_date, legacy=legacy)
        self.on_date = on_date
        self.legacy = legacy  # CB RF radically changed format from DBF (legacy) to XML.

    def __getitem__(self, item):
        """
        :param str item:
        :rtype: Bank
        """
        key = 'swift' if len(item) in {8, 11} else 'bic'
        indexed = {getattr(bank, key): bank for bank in self.banks}

        return indexed[item]

    @classmethod
    def get_titles(cls):
        """Returns fields titles.

        :rtype: OrderedDict
        """
        titles = OrderedDict((
            ('bic', 'БИК'),  # Банковский идентификационный код
            ('swift', 'Код SWIFT'),
            ('name', 'Название'),
            ('name_full', 'Полное название'),
            ('name_full_eng', 'Полное название (англ.)'),

            ('date_added', 'Дата добавления записи'),
            ('date_updated', 'Дата обновления записи'),
            ('date_change', 'Дата изменения реквизитов'),

            ('restricted', 'С ограничениями'),  # Fuzzy analogy for `control_code`.
            ('restrictions', 'Ограничения'),
            ('control_code', 'Код контроля'),
            ('control_date', 'Дата контроля'),

            ('corr', 'Кор. счёт'),
            ('corr_bik', 'Кор. счёт (расчёты с БИК)'),

            ('regnum', 'Регистрационный номер'),
            ('mfo', 'Номер МФО'),
            ('okpo', 'Номер ОКПО'),  # Классификатор предприятий и организаций
            ('type', 'Тип'),
            ('pay_type', 'Тип расчётов'),

            ('country_code', 'Код страны'),
            ('region_code', 'Код региона ОКАТО'),  # Классификатор объектов административно-территориального деления
            ('region', 'Регион'),
            ('zip', 'Индекс'),
            ('place_type', 'Тип населённого пункта'),
            ('place', 'Населённый пункт'),
            ('address', 'Адрес'),

            ('phone', 'Телефон'),
            ('telegraph', 'Телеграф'),
            ('commutator', 'Коммутатор'),

            ('rkc_bic', 'БИК РКЦ'),  # Рассчётно-кассовый центр
            ('term', 'Срок проведения расчётов (дней)'),
        ))
        return titles

    @classmethod
    def annotate(cls, banks):
        """Annotates bank objects with titles.

        :param list[Bank] banks: A list of Bank objects to annotate.

        :rtype: list

        """
        titles = cls.get_titles()
        annotated = []

        def pick_value(in_dict):
            for key in ['name', 'fullname', 'uername']:
                val = in_dict.get(key)
                if val:
                    return val
            return '<no name>'

        unset = object()

        for bank in banks:
            bank_dict = OrderedDict()
            bank = bank._asdict()

            for alias, title in titles.items():
                value = bank.get(alias, unset)

                if value is unset:
                    # Some fields may be missing in Bank/BankLegacy
                    continue

                if isinstance(value, tuple):
                    value = pick_value(value._asdict())

                elif isinstance(value, bool):
                    value = 'Да' if value else 'Нет'

                elif isinstance(value, list):
                    value = '\n  ' + '\n  '.join(map(text_type, value))

                bank_dict[title] = value or ''

            annotated.append(bank_dict)

        return annotated

    @classmethod
    def _get_archive(cls, url):
        LOG.debug('Fetching data from %s ...', url)

        response = cls._get_response(url, stream=True)
        return BytesIO(response.content)

    @classmethod
    def _read_zipped_xml(cls, zipped):

        with ZipFile(zipped, 'r') as zip_:
            filename = zip_.namelist()[0]

            with zip_.open(filename) as f:
                return ElementTree.fromstring(f.read())

    @classmethod
    def _get_data(cls, on_date, legacy=False):

        if legacy:
            return cls._get_data_dbf(on_date=on_date)

        return cls._get_data_xml(on_date=on_date)

    @classmethod
    def _get_data_xml(cls, on_date):
        """Справочник БИК (Клиентов Банка России). XML ED807

        http://www.cbr.ru/development/formats/

        :param datetime on_date:
        :rtype: list

        """
        url = 'http://www.cbr.ru/VFS/mcirabis/BIKNew/%sED01OSBR.zip' % on_date.strftime('%Y%m%d')

        xml = cls._read_zipped_xml(cls._get_archive(url))

        def parse_date(val):
            if not val:
                return val
            return datetime.strptime(val, '%Y-%m-%d').date()

        ns = '{urn:cbr-ru:ed:v2.0}'

        types = {
            '00': 'Главное управление Банка России',
            '10': 'Расчетно-кассовый центр',
            '12': 'Отделение, отделение – национальный банк главного управления Банка России',
            '15': 'Структурное подразделение центрального аппарата Банка России',
            '16': 'Кассовый центр',
            '20': 'Кредитная организация',
            '30': 'Филиал кредитной организации',
            '40': 'Полевое учреждение Банка России',
            '51': 'Федеральное казначейство',
            '52': 'Территориальный орган Федерального казначейства',
            '60': 'Иностранная кредитная организация',
            '65': 'Иностранный центральный (национальный) банк',
            '71': 'Клиент кредитной организации, являющийся косвенным участником',
            '75': 'Клиринговая организация',
            '78': 'Внешняя платежная система',
            '90': 'Конкурсный управляющий (ликвидатор, ликвидационная комиссия)',
            '99': 'Клиент Банка России, не являющийся участником платежной системы',
        }
        """УФЭБС_2021_1_1_КБР_Кодовые_Значения.pdf
        77 Тип участника перевода
        
        """

        banks = []

        for entry in xml.findall(ns + 'BICDirectoryEntry'):
            restrictions_applied = []

            bic = entry.attrib['BIC']

            el_info = entry.find(ns + 'ParticipantInfo')
            attrs_info = el_info.attrib

            if attrs_info['ParticipantStatus'] == 'PSDL':  # Маркер удаления
                continue

            for el_restriction in el_info.findall(ns + 'RstrList'):
                attrs = el_restriction.attrib
                code = attrs['Rstr']
                restrictions_applied.append(Restriction(
                    code=code,
                    date=datetime.strptime(attrs['RstrDate'], '%Y-%m-%d').date(),
                ))

            swiftcode = None

            for el_swift in entry.findall(ns + 'SWBICS'):
                if el_swift.attrib.get('DefaultSWBIC'):
                    swiftcode = el_swift.attrib['SWBIC']  # [8/11]
                    break

            corr = ''
            accounts = entry.findall(ns + 'Accounts')

            for el_account in accounts:
                """
                @DateIn - Дата открытия счета [YY-mm-dd]
                @Check
                @AccountCBRBIC
                
                """
                attrs = el_account.attrib

                if attrs['AccountStatus'] == 'ACDL':  # [4]  Маркер удаления
                    continue

                if attrs['RegulationAccountType'] != 'CRSA':  # [4]
                    """
                    CBRA Счет Банка России
                    CRSA Корреспондентский счет
                    BANA Банковский счет
                    TRSA Счет Федерального казначейства
                    TRUA Счет доверительного управления
                    CLAC Клиринговый счет
                    UTRA Единый казначейский счет
                    
                    """
                    continue

                assert corr == '', 'More than one correspondent account detected'
                corr = attrs['Account']  # [20]

                for el_restriction in el_account.findall(ns + 'AccRstrList'):
                    attrs = el_restriction.attrib
                    code = attrs['AccRstr']
                    restrictions_applied.append(Restriction(
                        code=code,
                        date=datetime.strptime(attrs['AccRstrDate'], '%Y-%m-%d').date(),
                        account=corr,
                    ))

            banks.append(Bank(
                bic=bic,  # [9]
                name_full=attrs_info['NameP'],  # [160]
                name_full_eng=attrs_info.get('EnglName', ''),  # [140]
                region_code=attrs_info['Rgn'],  # [2] 00 - за пределами РФ
                country_code=attrs_info.get('CntrCd', ''),  # [2]
                zip=attrs_info.get('Ind', ''),  # [6]
                place_type=attrs_info.get('Tnp', ''),  # [5]
                place=attrs_info.get('Nnp', ''),  # [25]
                address=attrs_info.get('Adr', ''),  # [160]
                regnum=attrs_info.get('RegN', ''),  # [9]
                type=types.get(attrs_info['PtType'], ''),  # [2]
                date_added=parse_date(attrs_info['DateIn']),
                corr=corr,
                swift=swiftcode,
                restricted=bool(restrictions_applied),
                restrictions=restrictions_applied,
            ))

        return banks

    @classmethod
    def _read_zipped_db(cls, zipped, filename):
        with Dbf.open_zip(filename, zipped, case_sensitive=False) as dbf:
            for row in dbf:
                yield row

    @classmethod
    def _get_data_dbf(cls, on_date):
        """

        :param datetime on_date:
        :rtype: list

        """
        try:
            swifts = cls._get_data_swift()

        except PycbrfException:
            swifts = {}

        url = 'http://www.cbr.ru/vfs/mcirabis/BIK/bik_db_%s.zip' % on_date.strftime('%d%m%Y')
        zip = cls._get_archive(url)

        def get_indexed(dbname, index):
            return {getattr(region, index): region for region in cls._read_zipped_db(zip, filename=dbname)}

        regions = get_indexed('reg.dbf', 'rgn')
        types = get_indexed('pzn.dbf', 'pzn')
        place_types = get_indexed('tnp.dbf', 'tnp')
        pay_types = get_indexed('uer.dbf', 'uer')

        banks = []

        for row in cls._read_zipped_db(zip, filename='bnkseek.dbf'):
            region_code = row.rgn
            bic = row.newnum

            telegraph = []
            row.at1 and telegraph.append(row.at1)
            row.at2 and telegraph.append(row.at2)

            term = row.srok or 0

            if term:
                term = int(term)

            control_code = row.real
            """
            БЛОК - прекращенией операций из-за блокировки
            ЗСЧТ - прекращенией операций из-за закрытия счёта филиала
            ИЗМР - прекращенией операций из-за изменения реквизитов
            ИНФО - предвариательное оповещение о скором прекращении операций
            ИСКЛ - предвариательное оповещение о начале процесса ликвизации
            ЛИКВ - говорит о создании ликвидационной комиссии
            ОТЗВ - отзыв лицензии, прекращение операций
            ВРФС - режим временного функционирование счёта
            """

            banks.append(BankLegacy(
                bic=bic,
                name=row.namen,
                name_full=row.namep,
                region_code=region_code,
                region=regions.get(region_code),
                zip=row.ind,
                place_type=place_types.get(row.tnp),
                place=row.nnp,
                address=row.adr,
                rkc_bic=row.rkc,
                term=term,
                date_added=row.date_in,
                date_updated=row.dt_izm,
                date_change=row.dt_izmr,
                mfo=row.permfo,
                corr=row.ksnp,
                corr_bik=row.newks,
                phone=row.telef,
                telegraph=','.join(telegraph),
                commutator=row.cks,
                okpo=row.okpo,
                regnum=row.regn,
                type=types[row.pzn],
                pay_type=pay_types[row.uer],
                control_code=control_code,
                control_date=row.date_ch,
                swift=swifts.get(bic),
            ))

        return banks

    @classmethod
    def _get_data_swift(cls):
        # At some moment static URL has became dynamic, and now ne need to search for it every time.
        host = 'http://www.cbr.ru'
        response = cls._get_response('%s/analytics/digest/' % host)

        found = re.findall('href="([^."]+\.zip)"', response.text)

        if not found or len(found) > 1:
            raise PycbrfException('Unable to get SWIFT info archive link')

        url = host + found[0]

        items = {
            item.kod_rus: item.kod_swift for item in
            cls._read_zipped_db(cls._get_archive(url), filename='bik_swif.dbf')
        }
        return items
