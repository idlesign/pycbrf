import pytest
from os import path


@pytest.fixture
def dir_fixtures(request):
    return path.join(path.dirname(path.abspath(request.module.__file__)), 'fixtures')


@pytest.fixture
def read_fixture(dir_fixtures):

    from io import BytesIO

    def read_fixture_(name):

        with open(path.join(dir_fixtures, name), 'rb') as f:
            data = f.read()

        return BytesIO(data)

    return read_fixture_
