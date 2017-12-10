class DatabaseError(Exception):
    """Raised when an database intitializes improperly"""
    pass


class EntryError(Exception):
    """Raised when there is an invalid happi entry"""
    pass


class DuplicateError(Exception):
    """Raised when a duplicate device is saved"""
    pass


class ContainerError(Exception):
    """Raised by an improperly setup container"""
    pass


class SearchError(Exception):
    """Raised when no device is found while searching"""
    pass
