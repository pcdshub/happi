"""
Base backend database options
"""
import logging

logger = logging.getLogger(__name__)


class _Backend:
    """
    Base class for backend database
    """

    @property
    def all_devices(self):
        """
        List of all device sub-dictionaries
        """
        raise NotImplementedError

    def find(self, multiples=False, **kwargs):
        """
        Find an instance or instances that matches the search criteria

        Parameters
        ----------
        multiples : bool
            Find a single result or all results matching the provided
            information

        kwargs :
            Requested information
        """
        raise NotImplementedError

    def save(self, _id, post, insert=True):
        """
        Save information to the database

        Parameters
        ----------
        _id : str
            ID of device

        post : dict
            Information to place in database

        insert : bool, optional
            Whether or not this a new device to the database

        Raises
        ------
        DuplicateError:
            If insert is True, but there is already a device with the provided
            _id

        SearchError:
            If insert is False, but there is no device with the provided _id

        PermissionError:
            If the write operation fails due to issues with permissions
        """
        raise NotImplementedError

    def delete(self, _id):
        """
        Delete a device instance from the database

        Parameters
        ----------
        _id : str
            ID of device

        Raises
        ------
        PermissionError:
            If the write operation fails due to issues with permissions
        """
        raise NotImplementedError
