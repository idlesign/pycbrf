import sys


PY3 = sys.version_info[0] == 3

if PY3:  # pragma: nocover
    string_types = str,

else:  # pragma: nocover
    string_types = basestring,
