import sys

import requests

PY3 = sys.version_info[0] == 3

if PY3:  # pragma: nocover
    string_types = str,
    text_type = str
    import io
    BytesIO = io.BytesIO

else:  # pragma: nocover
    string_types = basestring,
    text_type = unicode
    import StringIO
    BytesIO = StringIO.StringIO


class WithRequests(object):

    req_timeout = 10
    
    req_user_agent = (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/74.0.3729.169 YaBrowser/19.6.2.594 (beta) Yowser/2.5 Safari/537.36'
    )

    @classmethod
    def _get_response(cls, url, **kwargs):

        kwargs_ = {
            'timeout': cls.req_timeout,
            'headers': {
                'User-Agent': cls.req_user_agent
            },
        }
        kwargs_.update(kwargs)

        return requests.get(url, **kwargs_)
