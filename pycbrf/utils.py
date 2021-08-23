from datetime import datetime
from typing import Union

import requests


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
    _instances = {}

    def __call__(cls):
        if cls not in cls._instances:
            instance = super().__call__()
            cls._instances[cls] = instance
        return cls._instances[cls]


class FormatMixin:
    @staticmethod
    def _format_num_code(num: Union[int, str]) -> str:
        """Format integer or invalid string numeric code to ISO 4217 currency numeric code."""
        if isinstance(num, int) or (isinstance(num, str) and len(num) < 3):
            num_ = num
            if isinstance(num_, str):
                num_ = int(num_)
            return "{:03}".format(num_)
        return num

    @staticmethod
    def _date_from_string(date):
        if isinstance(date, str):
            return datetime.strptime(date, '%Y-%m-%d')
        return date
