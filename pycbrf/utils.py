from datetime import date, datetime
from typing import Union, Optional

import requests

TypeDateDef = Union[str, date, datetime]


class WithRequests:
    """Mixin to perform HTTP requests."""

    req_timeout: int = 10

    req_user_agent: str = (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/74.0.3729.169 YaBrowser/19.6.2.594 (beta) Yowser/2.5 Safari/537.36'
    )

    @classmethod
    def _get_response(cls, url: str, **kwargs) -> requests.Response:
        kwargs_ = {
            'timeout': cls.req_timeout,
            'headers': {
                'User-Agent': cls.req_user_agent,
            },
        }
        kwargs_.update(kwargs)

        return requests.get(url, **kwargs_)


class SingletonMeta(type):
    """Mixin for create Singleton pattern that restricts the instantiation of a class to one "single" instance"""
    _instances = {}

    def __call__(cls):
        if cls not in cls._instances:
            instance = super().__call__()
            cls._instances[cls] = instance
        return cls._instances[cls]


class FormatMixin:
    """Mixin for various argument formatting"""

    @staticmethod
    def _format_num_code(num: Union[int, str]) -> str:
        """Format integer or invalid string numeric code to ISO 4217 currency numeric code string."""

        return f'{num}'.zfill(3)

    @staticmethod
    def _date_format(value: datetime) -> str:
        """Format datetime into a string.

        :param value:

        """
        return value.strftime('%d/%m/%Y')

    @staticmethod
    def _date_parse(value: str) -> datetime:
        """Parse a string into a datetime.

        :param value:

        """
        return datetime.strptime(value, '%d.%m.%Y')

    @staticmethod
    def _get_datetime(value: TypeDateDef) -> Optional[datetime]:
        """Format date to datetime.datetime from string and datetime.date

        :param value:

        """
        if isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m-%d')

        elif isinstance(value, date):
            value = datetime(value.year, value.month, value.day)

        return value
