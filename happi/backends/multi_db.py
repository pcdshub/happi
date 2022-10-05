"""
Backend implementation that combines multiple backends.
"""
import functools
import logging
import os
import re
from typing import Any, Dict, Generator, List, Union

from .core import _Backend

logger = logging.getLogger(__name__)

PathLike = Union[str, bytes, os.PathLike]
ItemMeta = Dict[str, Any]


def prevent_duplicate_ids(fn):
    """
    Decorator that remembers which document _id's have been yielded and
    prevents subsequent documents with matching _id's from being yielded
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
    Multi-file backend.

    Combines multiple backends, prioritizing database files in order
    of appearance.

    """
    def __init__(self, backends: List[_Backend]):
        self._load_cache = None

        self.backends = backends

    @property
    def all_items(self) -> List[ItemMeta]:
        """
        List of all items in all backends.

        In the case of duplicate items, the item in the first backend
        takes priority.
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
    def find(
        self,
        *args,
        multiples=False,
        **kwargs
    ) -> Generator[ItemMeta, None, None]:
        """
        Find an instance or instances that matches the search criteria.

        Parameters
        ----------
        multiples : bool
            Find a single result or all results matching the provided
            information.
        kwargs
            Requested information.
        """
        for bknd in self.backends:
            yield from bknd.find(*args, **kwargs)

    def save(self, _id, post, insert=True):
        """The current implementation of this backend is read-only."""
        raise NotImplementedError("The Questionnaire backend is read-only")

    def delete(self, _id):
        """The current implementation of this backend is read-only."""
        raise NotImplementedError("The Questionnaire backend is read-only")

    def get_by_id(self, id_) -> ItemMeta:
        """
        Get an document by ID if it exists, or return None.

        Returns the first match, in config priority
        """
        for bknd in self.backends:
            doc = bknd.get_by_id(id_)
            if doc:
                return doc

        return

    @prevent_duplicate_ids
    def find_range(self, key, *, start, stop=None, to_match) -> Generator[ItemMeta, None, None]:
        """
        Find instances that match the search criteria, such that
        ``start <= entry[key] < stop``.

        Should check for duplicates

        Parameters
        ----------
        key : _type_
            _description_
        start : _type_
            _description_
        to_match : _type_
            _description_
        stop : _type_, optional
            _description_, by default None

        Yields
        ------
        Generator[ItemMeta, None, None]
            _description_
        """
        for bknd in self.backends:
            yield from bknd.find_range(key, start=start, stop=stop, to_match=to_match)

    @prevent_duplicate_ids
    def find_regex(self, to_match, *, flags=re.IGNORECASE):
        for bknd in self.backends:
            yield from bknd.find_regex(to_match, flags=flags)
