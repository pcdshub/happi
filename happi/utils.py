"""
Basic module utilities
"""


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
