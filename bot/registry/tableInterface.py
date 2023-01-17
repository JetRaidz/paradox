from .Connector import Connector
from .Interface import Interface
from .schemas import tableSchema


class tableInterface(Interface):
    """
    Data interface containing standard methods to access a single table.
    Acts as a  wrapper around the connector for a single table,
    with some optional type checking.
    """

    _mysql_schema = None
    _sqlite_schema = None

    def __init__(self, conn: Connector, table_name, app, column_data,
                 shared=True, app_column='app', app_column_primary=True,
                 mysql_schema=None, sqlite_schema=None):
        self.conn = conn
        self.table = table_name
        self.app = app
        self.shared = shared

        self.mysql_schema = mysql_schema or self._mysql_schema
        self.sqlite_schema = sqlite_schema or self._sqlite_schema

        self.columns = {p[0]: p[1] for p in column_data}
        self.app_column = app_column
        self.app_column_primary = app_column_primary

        if not self.shared and (self.app_column not in self.columns):
            raise ValueError("App column not found in non-shared table specification.")

    @classmethod
    def from_schema(cls, conn: Connector, app: str, schema: tableSchema, **kwargs):
        """
        Generates a tableInterface from a tableSchema.
        Trasparently passes remaining `kwargs` along to the constructor.
        """
        return cls(
            conn,
            schema.name,
            app,
            schema.interface_columns,
            mysql_schema=schema.for_mysql,
            sqlite_schema=schema.for_sqlite,
            **kwargs
        )

    @property
    def schema(self):
        if self.conn.db_type == "sqlite":
            return self.sqlite_schema
        elif self.conn.db_type == "mysql":
            return self.mysql_schema

    def check_keys(self, params):
        for param, value in params.items():
            if param not in self.columns:
                raise ValueError("Invalid column '{}' passed to table interface '{}'".format(param, self.table))
            elif self.columns[param] is not None:
                if (not isinstance(value, self.columns[param]) and
                        not isinstance(value, (list, tuple)) and
                        value is not None):
                    raise TypeError("Incorrect type '{}' passed for key '{}' in table interface '{}'".format(
                        type(value), param, self.table
                    ))
                elif (isinstance(value, (list, tuple)) and
                        not all(isinstance(item, self.columns[param]) for item in value)):
                    raise TypeError("Incorrect type in list passed for key '{}' in table interface '{}'".format(
                        param, self.table
                    ))

    def add_app(self, params):
        """
        Add app to parameters for non-shared tables.
        """
        if not self.shared and self.app_column not in params:
            params[self.app_column] = self.app

    def select_where(self, select_columns=None, **conditions):
        self.check_keys(conditions)
        self.add_app(conditions)
        return self.conn.select_where(self.table, select_columns=select_columns, **conditions)

    def select_one_where(self, *args, **kwargs):
        rows = self.select_where(*args, **kwargs)
        return rows[0] if rows else None

    def update_where(self, valuedict, **conditions):
        self.check_keys(conditions)
        self.add_app(conditions)
        return self.conn.update_where(self.table, valuedict, **conditions)

    def delete_where(self, **conditions):
        self.check_keys(conditions)
        self.add_app(conditions)
        return self.conn.delete_where(self.table, **conditions)

    def insert(self, allow_replace=False, **values):
        self.check_keys(values)
        self.add_app(values)
        return self.conn.insert(self.table, allow_replace=allow_replace, **values)

    def insert_many(self, *value_tuples, insert_keys=None):
        """
        Note that insert_many does not support automatic app insertion or value checking without `insert_keys`.
        """
        if insert_keys:
            # Value checking
            for v_tuple in value_tuples:
                values = {key: value for key, value in zip(insert_keys, v_tuple)}
                self.check_keys(values)

            # App insertion
            if not self.shared and self.app_column not in insert_keys:
                insert_keys = (*insert_keys, self.app_column)
                value_tuples = [(*tup, self.app) for tup in value_tuples]

        return self.conn.insert_many(self.table, *value_tuples, insert_keys=insert_keys)

    def upsert(self, constraint, add_app_constraint=True, **values):
        self.check_keys(values)
        self.add_app(values)
        if add_app_constraint and not self.shared and self.app_column_primary:
            if isinstance(constraint, str):
                constraint = (constraint, self.app_column)
            else:
                constraint = (*constraint, self.app_column)

        return self.conn.upsert(self.table, constraint, **values)
