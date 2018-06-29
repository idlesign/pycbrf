import sys


PY3 = sys.version_info[0] == 3

if PY3:  # pragma: nocover
    string_types = str,
    import io
    BytesIO = io.BytesIO

else:  # pragma: nocover
    string_types = basestring,
    import StringIO
    BytesIO = StringIO.StringIO
