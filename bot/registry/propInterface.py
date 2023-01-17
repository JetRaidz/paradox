from .Interface import Interface
from .connectors import Connector


class propInterface(Interface):
    """
    Basic key-value data interface supporting shared and unshared app data.
    Only supports integer keys, string property names, and string values.
    """
    def __init__(self, conn: Connector, table_name, keys, app_name):
        self.conn = conn
        self.table = table_name
        self.app = app_name
        self.keys = keys

        self.maptable = "{}_props".format(table_name)
        self.prop_map = None  # Set in _get_propmap

    @property
    def schema(self):
        """
        Generate creation schema
        """
        # Different db types have different column type specifications
        if self.conn.db_type == "sqlite":
            strcol = "TEXT"
            shortstrcol = "TEXT"
            intcol = "INTEGER"
            boolcol = "BOOLEAN"
        elif self.conn.db_type == "mysql":
            shortstrcol = "VARCHAR(16)"
            strcol = "VARCHAR(2047)"
            intcol = "BIGINT"
            boolcol = "BOOL"

        # Generate property map table schema
        maptable_schema = (
            "CREATE TABLE {table}(\n"
            "\tproperty {shortstrcol} NOT NULL,\n"
            "\tshared {boolcol} NOT NULL,\n"
            "\tPRIMARY KEY (property)\n"
            ");".format(
                table=self.maptable,
                shortstrcol=shortstrcol,
                boolcol=boolcol
            ))

        # Generate property table schema
        # Key column list
        key_columns = ["{} {} NOT NULL".format(key, intcol) for key in self.keys]
        key_column_str = "{},\n\t".format(",\n\t".join(keycol for keycol in key_columns)) if self.keys else ""

        # Key primary key list
        key_list = "{}, ".format(", ".join(self.keys)) if self.keys else ""

        maintable_schema = (
            "CREATE TABLE {table}(\n"
            "\t{key_column_str}property {shortstrcol} NOT NULL,\n"
            "\tvalue {strcol},\n"
            "\tPRIMARY KEY ({key_list}property),\n"
            "\tFOREIGN KEY (property)\n"
            "\t\tREFERENCES {maptable} (property)\n"
            ");".format(
                table=self.table,
                key_column_str=key_column_str,
                shortstrcol=shortstrcol,
                strcol=strcol,
                key_list=key_list,
                maptable=self.maptable
            )
        )

        return "{}\n\n{}".format(maptable_schema, maintable_schema)

    # Internal property mapping methods
    def _get_propmap(self):
        """
        Load and return the property map dictionary
        from the property table.
        """
        prop_map = {}
        for prop in self.conn.select_where(self.maptable):
            prop_map[prop["property"]] = prop["shared"]
        self.prop_map = prop_map

    def _map_prop(self, prop):
        """
        Return the app-aware name of the property key
        """
        if self.app:
            # Get the propmap if it doesn't exist
            if not self.prop_map:
                self._get_propmap()

            # Return the mapped prop
            if not self.prop_map.get(prop, True):
                return "{}_{}".format(self.app, prop)
            else:
                return prop
        else:
            return prop

    def ensure_exists(self, *props, shared=True, update=False):
        """
        Ensure that the specified properties exist in the property map.
        Creates them if they do not exist.
        If they do exist but have a different shared value,
        updates the property if update is set, otherwise raises ValueError.
        """
        # Get the propmap if it doesn't exist
        if not self.prop_map:
            self._get_propmap()

        for prop in props:
            if prop in self.prop_map:
                if self.prop_map[prop] != shared:
                    if update:
                        # Update the shared value
                        values = {"shared": shared}
                        self.conn.update_where(self.maptable, values, property=prop)
                    else:
                        # Raise value error
                        raise ValueError(
                            "Incorrect shared value '{}' passed for property '{}' of table '{}'".format(
                                shared,
                                prop,
                                self.table
                            )
                        )
            else:
                # Add property to property table
                self.conn.insert(self.maptable, property=prop, shared=shared)

    # Getters and setters
    def get(self, *args):
        """
        Retrieve the value of a property, or None if it is not set.
        """
        # Catch incorrect number of args passed
        if len(args) != len(self.keys) + 1:
            raise ValueError("Incorrect number of arguments passed.")

        # Extract property and keys
        prop = self._map_prop(args[-1])
        keys = args[:-1]

        # Build dictionary of keys
        key_dict = {keyname: key for (keyname, key) in zip(self.keys, keys)}

        # Retrieve requested value
        results = self.conn.select_where(
            self.table,
            select_columns=['value'],
            property=prop,
            **key_dict
        )

        # Return the result, or None if there was no result
        return results[0]["value"] if results else None

    def set(self, *args):
        """
        Set a property
        """
        # Catch incorrect number of args passed
        if len(args) != len(self.keys) + 2:
            raise ValueError("Incorrect number of arguments passed.")

        keys = args[:-2]
        prop = self._map_prop(args[-2])
        value = args[-1]

        # Catch non-string value
        if not isinstance(value, str):
            raise TypeError("Unsupported value type '{}'".format(type(value)))

        # Build dictionary of keys
        key_dict = {keyname: key for (keyname, key) in zip(self.keys, keys)}

        # Set or update the property
        return self.conn.insert(
            self.table,
            allow_replace=True,
            property=prop,
            value=value,
            **key_dict
        )

    def unset(self, *args):
        """
        Unset (delete) a property
        """
        # Catch incorrect number of args passed
        if len(args) != len(self.keys) + 1:
            raise ValueError("Incorrect number of arguments passed.")

        # Extract property and keys
        prop = self._map_prop(args[-1])
        keys = args[:-1]

        # Build dictionary of keys
        key_dict = {keyname: key for (keyname, key) in zip(self.keys, keys)}

        # Delete value (if it exists)
        return self.conn.delete_where(
            self.table,
            property=prop,
            **key_dict
        )

    def get_all_with(self, prop):
        """
        Retrieves all rows matching the specified property
        """
        prop = self._map_prop(prop)
        return self.conn.select_where(
            self.table,
            property=prop
        )

    def select_where(self, **kwargs):
        """
        Pass-through interface to `self.conn.select_where`.
        """
        return self.conn.select_where(self.table, **kwargs)
