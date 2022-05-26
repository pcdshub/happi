"""
Basic module utilities
"""
import keyword
import logging

from happi.errors import EnforceError

logger = logging.getLogger(__name__)


def create_alias(name):
    """
    Clean an alias to be an acceptable Python variable
    """
    return name.replace(' ', '_').replace('.', '_').lower()


def get_happi_entry_value(entry, key, search_extraneous=True):
    extraneous = entry.extraneous
    value = getattr(entry, key, None)
    if value is None and search_extraneous:
        # Try to look at extraneous
        value = extraneous.get(key, None)

    if not value:
        raise ValueError('Invalid Key for Device.')
    return value


def is_number(str_value):
    """
    Checks if it is a valid float number
    """
    try:
        float(str_value)
        return True
    except ValueError:
        return False


def is_a_range(str_value):
    """
    Checks to see if it is a range.
    It needs to have two valid values separated by a comma.
    Ex:
        1,100
        -2,8
        100,2
    """
    if ',' in str_value:
        start, stop = str_value.split(',')
        if is_number(start) and is_number(stop):
            return True
        else:
            logger.error("Possibly provided invalid numbers for a range")
            return False
    else:
        return False


def is_valid_identifier_not_keyword(str_value):
    try:
        if str.isidentifier(str_value) and not keyword.iskeyword(str_value):
            return str_value
    except Exception:
        pass
    raise EnforceError(f'{str_value} is either not a valid Python identifier, '
                       'or is a reserved keyword.')


class OptionalDefault():
    """
    Dummy object to pass to click.prompt if there is no default

    Simply meant to be unique, to avoid collisions with real defaults
    """
    def __str__(self):
        return 'optional'


def optional_enforce(enforce_value):
    def inner(value):
        if isinstance(value, OptionalDefault):
            return value
        else:
            return enforce_value(value)

    return inner
