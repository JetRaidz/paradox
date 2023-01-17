from enum import Enum


class tableElement:
    """
    Abstract base class describing an element of a table schema.
    Examples include columns, constraints, indexes, and data.
    """
    def __init__(self, *args, **kwargs):
        self.table = None

    @property
    def for_mysql(self):
        raise NotImplementedError

    @property
    def for_sqlite(self):
        raise NotImplementedError


class ColumnType(Enum):
    """
    Describes several common database column data types,
    and describes the types for python, mysql and sqlite.
    """
    INT = (int, 'INT', 'INTEGER')
    SNOWFLAKE = (int, 'BIGINT', 'INTEGER')
    SHORTSTRING = (str, 'VARCHAR(64)', 'TEXT')
    MSGSTRING = (str, 'VARCHAR(2048)', 'TEXT')
    TEXT = (str, 'TEXT', 'TEXT')
    BOOL = (bool, 'BOOLEAN', 'BOOL')
    TIMESTAMP = (int, 'TIMESTAMP', 'TIMESTAMP')

    @property
    def pytype(self):
        return self.value[0]

    @property
    def in_mysql(self):
        return self.value[1]

    @property
    def in_sqlite(self):
        return self.value[2]


class Column(tableElement):
    """
    Simple class to describe a column in a simple table design.

    Parameters
    ----------
    column_name: str
        Name of the column being described.
    column_type: ColumnType
        Type of the column.
    primary: Bool
        Whether this column is a primary key.
    required: Bool
        Whether this column is required not to be NULL.
    default: Any
        The default value for the column.
    mysql_update_timestamp: Bool
        Whether to add `ON UPDATE CURRENT_TIMESTAMP` to the column.
        Only applies to mysql.
    """
    def __init__(self, column_name, column_type,
                 primary=False, required=False, autoincrement=False, default=None,
                 mysql_update_timestamp=False):
        super().__init__()
        self.name = column_name
        self.col_type = column_type
        self.primary = primary
        self.required = required
        self.autoincrement = autoincrement
        self.default = default
        self.update_timestamp = mysql_update_timestamp

    @property
    def for_mysql(self):
        return "{} {}{}{}{}{}".format(
            self.name,
            self.col_type.in_mysql,
            " NOT NULL" if self.required else "",
            " AUTO_INCREMENT " if self.autoincrement else "",
            " DEFAULT {}".format(self.default) if self.default is not None else "",
            " ON UPDATE CURRENT_TIMESTAMP" if self.update_timestamp else ""
        )

    @property
    def for_sqlite(self):
        return "{} {}{}{}{}".format(
            self.name,
            self.col_type.in_sqlite,
            " NOT NULL" if self.required else "",
            " PRIMARY KEY AUTOINCREMENT " if self.autoincrement else "",
            " DEFAULT {}".format(self.default) if self.default is not None else ""
        )


class ReferenceAction(Enum):
    RESTRICT = "RESTRICT"
    CASCADE = "CASCADE"
    SETNULL = "SET NULL"


class ForeignKey(tableElement):
    def __init__(self, local_keys, foreign_table, foreign_keys, on_delete=None):
        super().__init__()
        self.local_keys = local_keys
        self.foreign_table = foreign_table
        self.foreign_keys = foreign_keys
        self.on_delete = on_delete

    @property
    def for_mysql(self):
        return "FOREIGN KEY ({}) REFERENCES {}({}){}".format(
            self.local_keys,
            self.foreign_table,
            self.foreign_keys,
            " ON DELETE {}".format(self.on_delete.value) if self.on_delete is not None else ""
        )

    @property
    def for_sqlite(self):
        return "FOREIGN KEY ({}) REFERENCES {}({}){}".format(
            self.local_keys,
            self.foreign_table,
            self.foreign_keys,
            " ON DELETE {}".format(self.on_delete.value) if self.on_delete is not None else ""
        )


class Index(tableElement):
    def __init__(self, name, *keys):
        super().__init__()
        self.name = name
        self.keys = keys

    @property
    def for_mysql(self):
        return "CREATE INDEX {} ON {}({});".format(
            self.name,
            self.table,
            ','.join(self.keys)
        )

    @property
    def for_sqlite(self):
        return "CREATE INDEX {} ON {}({});".format(
            self.name,
            self.table,
            ','.join(self.keys)
        )


class RawElement(tableElement):
    def __init__(self, for_mysql, for_sqlite):
        super().__init__()
        self._for_mysql = for_mysql
        self._for_sqlite = for_sqlite

    @property
    def for_mysql(self):
        return self._for_mysql

    @property
    def for_sqlite(self):
        return self._for_sqlite
