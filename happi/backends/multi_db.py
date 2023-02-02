"""
Backend implementation that combines multiple backends.
"""
import functools
import logging
import re
from typing import Any, Optional, Union

from .core import ItemMeta, ItemMetaGen, _Backend

logger = logging.getLogger(__name__)


def prevent_duplicate_ids(fn):
    """
    Decorator that remembers which document _id's have been yielded and
    prevents subsequent documents with matching _id's from being yielded

    Expects the wrapped function to yield ItemMeta documents
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        unique_ids = set()
        for doc in fn(*args, **kwargs):
            if doc['_id'] not in unique_ids:
                unique_ids.add(doc['_id'])
                yield doc

    return wrapper


class MultiBackend(_Backend):
    """
    Multi-backend backend.

    Combines multiple backends, prioritizing database files in order
    of appearance.

    Parameters
    ----------
    backends : List[_Backend]
        A list of instantiated backends in order of priority.
        The backend at index 0 will have the highest priority.
    """
    def __init__(self, backends: list[_Backend]):
        self.backends = backends

    @property
    def all_items(self) -> list[ItemMeta]:
        """
        List of all items in all backends.

        In the case of duplicate items, the item in the first backend
        takes priority.

        Returns
        -------
        List[ItemMeta]
            A list of all metadata documents
        """
        items = []
        unique_ids = set()
        for bknd in self.backends:
            curr_items = bknd.all_items
            for doc in curr_items:
                if doc['_id'] not in unique_ids:
                    items.append(doc)
                    unique_ids.add(doc['_id'])

        return items

    def clear_cache(self) -> None:
        """
        Request to clear any cached data.

        Clears the cache of each backend
        """
        for bknd in self.backends:
            bknd.clear_cache()

    @prevent_duplicate_ids
    def find(self, *args, multiples=False, **kwargs) -> ItemMetaGen:
        """
        Find an instance or instances that matches the search criteria.

        Parameters
        ----------
        multiples : bool
            Find a single result or all results matching the provided
            information.
        kwargs
            Requested information.

        Yields
        ------
        Dict[str, Any]
            A generator of metadata documents
        """
        for bknd in self.backends:
            yield from bknd.find(*args, **kwargs)

    def save(self, _id, post, insert=True):
        """The current implementation of this backend is read-only."""
        raise NotImplementedError("The Multi-backend backend is read-only")

    def delete(self, _id):
        """The current implementation of this backend is read-only."""
        raise NotImplementedError("The Multi-backend backend is read-only")

    def get_by_id(self, id_: str) -> Optional[ItemMeta]:
        """
        Get an document by ID if it exists, or return None.

        Returns the first match, in config priority

        Parameters
        ----------
        id_ : str
            id to search for

        Returns
        -------
        Dict[str, Any] or None
            The requested metadata document
        """
        for bknd in self.backends:
            doc = bknd.get_by_id(id_)
            if doc:
                return doc

        return

    @prevent_duplicate_ids
    def find_range(
        self,
        key: str,
        *,
        start: Union[int, float],
        stop: Optional[Union[int, float]] = None,
        to_match: dict[str, Any]
    ) -> ItemMetaGen:
        """
        Find instances that match the search criteria, such that
        ``start <= entry[key] < stop``.

        Reports the document in the highest priority backend in the
        case of duplicates

        Parameters
        ----------
        key : str
            The database key to search
        start : Union[int, float]
            Inclusive minimum value to filter ``key`` on.
        to_match : Dict[str, Any]
            Exclusive maximum value to filter ``key`` on.
        stop : Union[int, float], optional
            Requested information, where the values must match exactly.

        Yields
        ------
        Dict[str, Any]
            metadata documents matching the provided range
        """
        for bknd in self.backends:
            yield from bknd.find_range(key, start=start, stop=stop,
                                       to_match=to_match)

    @prevent_duplicate_ids
    def find_regex(
        self,
        to_match: dict[str, Any],
        *,
        flags=re.IGNORECASE
    ) -> ItemMetaGen:
        """
        Find an instance or instances that matches the search criteria,
        using regular expressions.

        Parameters
        ----------
        to_match : dict
            Requested information, where the values are regular expressions.
        flags : RegexFlag
            flags to modify regex pattern parsing

        Yields
        ------
        Dict[str, Any]
            matching metadata documents
        """
        for bknd in self.backends:
            yield from bknd.find_regex(to_match, flags=flags)
