from typing import Any, List

from cmdClient import cmdClient

from registry import tableInterface  # noqa, imported for typing


class _tableData:
    """
    Abstract base for guild setting data mixins working on a single tableInterface.
    """
    # Name of table interface to use for storage access
    _table_interface_name = None

    # Name of the column storing the guild id
    _guildid_column = "guildid"

    # Name of the column with the desired data
    _data_column = None

    @classmethod
    def _get_table_interface(cls, client: cmdClient):
        """
        Gets the table interface from the client.
        """
        return client.data.interfaces.get(cls._table_interface_name)

    @classmethod
    def _reader(cls, client: cmdClient, guildid: int, **kwargs):
        """
        Read a setting from storage and return setting data or None.
        """
        raise NotImplementedError

    @classmethod
    def _writer(cls, client: cmdClient, guildid: int, data: Any, **kwargs):
        """
        Write provided setting data to storage.
        If the data is None, the setting is empty and should be unset.
        """
        raise NotImplementedError


class ListData(_tableData):
    """
    Mixin for list types implemented on a tableInterface.
    Implements a reader and writer.
    """
    @classmethod
    def _reader(cls, client: cmdClient, guildid: int, **kwargs):
        """
        Read in all entries associated to the guild.
        """
        table = cls._get_table_interface(client)  # type: tableInterface
        params = {
            "select_columns": [cls._data_column],
            cls._guildid_column: guildid
        }
        rows = table.select_where(**params)
        data_rows = [row[cls._data_column] for row in rows]
        return data_rows if data_rows else None

    @classmethod
    def _writer(cls, client: cmdClient, guildid: int, data: List[Any], **kwargs):
        """
        Write the provided list to storage.
        """
        # TODO: Accept kwargs for pure addition or removal of items
        # TODO: Compare existing values in table to avoid double-handling data
        # TODO: Transaction lock on the table so this is atomic

        table = cls._get_table_interface(client)  # type: tableInterface

        # Handle special case of data being None first
        if data is None:
            params = {
                cls._guildid_column: guildid
            }
            table.delete_where(**params)
            return

        current = cls._reader(client, guildid, **kwargs)
        if current is not None:
            to_insert = [item for item in data if item not in current]
            to_remove = [item for item in current if item not in data]
        else:
            to_insert = data
            to_remove = None

        # Handle required deletions
        if to_remove:
            params = {
                cls._guildid_column: guildid,
                cls._data_column: to_remove
            }
            table.delete_where(**params)

        # Handle required insertions
        if to_insert:
            columns = (cls._guildid_column, cls._data_column)
            values = [(guildid, value) for value in to_insert]
            table.insert_many(*values, insert_keys=columns)


class ColumnData(_tableData):
    """
    Mixin for data types represented in a single row and column of a tableInterface.
    Intended to be used with tables where `guildid` is the only primary key.
    """
    # Whether to delete if the writer is passed 'None'
    _delete_on_none = True

    # Constraint used for writing upsert. By default uses _guildid_column
    _upsert_constraint = None

    @classmethod
    def _reader(cls, client: cmdClient, guildid: int, **kwargs):
        """
        Read in the requested entry associated to the guild.
        """
        table = cls._get_table_interface(client)  # type: tableInterface
        params = {
            "select_columns": [cls._data_column],
            cls._guildid_column: guildid
        }
        rows = table.select_where(**params)
        return rows[0][cls._data_column] if rows else None

    @classmethod
    def _writer(cls, client: cmdClient, guildid: int, data: Any, **kwargs):
        """
        Write the provided entry to the table, allowing replacements.
        """
        table = cls._get_table_interface(client)  # type: tableInterface
        params = {
            cls._guildid_column: guildid
        }

        if data is None and cls._delete_on_none:
            # Handle deletion
            table.delete_where(**params)
        else:
            # Handle insert or update
            params[cls._data_column] = data
            table.upsert(
                constraint=cls._upsert_constraint or cls._guildid_column,
                **params
            )


class BoolData(_tableData):
    """
    Mixin for Boolean types implemented on a single column tableInterface.
    Implements a reader and writer.
    """
    @classmethod
    def _reader(cls, client: cmdClient, guildid: int, **kwargs):
        """
        Read the table and return whether the specified guildid exists.
        """
        table = cls._get_table_interface(client)  # type: tableInterface
        params = {
            cls._guildid_column: guildid
        }
        rows = table.select_where(**params)
        return len(rows) > 0

    @classmethod
    def _writer(cls, client: cmdClient, guildid: int, data: bool, **kwargs):
        """
        Write the provided boolean to storage by adding or removing the row.
        """
        table = cls._get_table_interface(client)  # type: tableInterface

        params = {
            cls._guildid_column: guildid,
        }
        if not data:
            # Delete all rows with the guildid
            table.delete_where(**params)
        else:
            # Upsert the row with the guildid
            table.upsert(constraint=cls._guildid_column, **params)
