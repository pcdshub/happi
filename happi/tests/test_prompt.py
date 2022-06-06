from typing import Any

import pytest
from click.testing import CliRunner

from happi.prompt import enforce_list, read_user_dict
from happi.utils import EnforceError


def test_user_dict(runner: CliRunner):
    default_dict = {'default_key': 'default_value'}

    # normal operation
    with runner.isolation('key1\nvalue1'):
        result = read_user_dict('prompt', default=default_dict)

    assert result == {'key1': 'value1'}

    # read default
    with runner.isolation('\n'):
        result = read_user_dict('prompt', default=default_dict)

    assert result == default_dict

    # reject keywords
    with runner.isolation('is\nnotis\n1\n'):
        result = read_user_dict('prompt', default=default_dict)

    assert result == {'notis': 1}

    # replace values
    with runner.isolation('key\n1\nkey\n2'):
        result = read_user_dict('prompt', default=default_dict)

    assert result == {'key': 2}


@pytest.mark.parametrize('user_in', (
    ['a', 'b', 2, 3],
    "['a', 'b', 2, 3]"
))
def test_enforce_list(user_in: Any):
    result = enforce_list(user_in)
    assert result == ['a', 'b', 2, 3]


@pytest.mark.parametrize('user_in', (
    'a',
    "['a', 'b'=2, 2, 3]",
    '[1,2,3,4.5.4]'
))
def test_enforce_list_fail(user_in: str):
    with pytest.raises(EnforceError):
        _ = enforce_list(user_in)
