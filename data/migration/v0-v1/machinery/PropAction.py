# import logging
from enum import Enum
from . import Connector


class InsertType(Enum):
    INSERT = 0
    UPSERT = 1
    MANY = 2


class ColumnKeys(Enum):
    VALUE = 'value'
    USERID = 'userid'
    SERVERID = 'serverid'


class PropAction:
    _connector: Connector = None

    def __init__(self, name, parser, target, insert_type, *insertmaps, constraint=None):
        self.name = name  # Name of the property
        self.parser = parser  # Parser function used to interpret value
        self.target = target  # Name of the target table
        self.insert_type = insert_type  # The relevant InsertType
        self.insertmaps = insertmaps  # The insert keymaps to apply to the row
        self.constraint = constraint  # Upsert constraint, only valid for sqlite (and postgres if we supported that)

    @classmethod
    def attach_connector(cls, connector):
        """
        Attach the given Connector
        """
        cls._connector = connector

    def substitue(self, key, row):
        """
        Substitute an insertmap key for the required value
        """
        if isinstance(key, ColumnKeys):
            return row[key.value]
        else:
            return key

    def act_on(self, row):
        """
        Apply the action to the given row.
        The row is expected to support the `Dict` interface, with column names as keynames.
        """
        prop_value = self.parser(row['value'])
        if prop_value is None:
            # Ignore empty values
            return

        # Shallow copy the row into a mutable dict
        row = dict(row)

        # Handler the various insert modes
        if self.insert_type == InsertType.INSERT:
            row['value'] = prop_value
            for insertmap in self.insertmaps:
                params = {col: self.substitue(key, row) for col, key in insertmap.items()}
                self._connector.insert(self.target, allow_replace=True, **params)
        elif self.insert_type == InsertType.UPSERT:
            row['value'] = prop_value
            for insertmap in self.insertmaps:
                params = {col: self.substitue(key, row) for col, key in insertmap.items()}
                self._connector.upsert(self.target, self.constraint, **params)
        elif self.insert_type == InsertType.MANY:
            if not prop_value:
                # Ignore empty lists
                return

            for insertmap in self.insertmaps:
                values = []
                for value in prop_value:
                    row['value'] = value
                    values.append(tuple(self.substitue(key, row) for key in insertmap.values()))
                self._connector.insert_many(
                    self.target,
                    *values,
                    allow_replace=True,
                    insert_keys=tuple(insertmap.keys())
                )
