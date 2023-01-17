import sqlite3 as sq

try:
    import mysql.connector
    MYSQL = True
except ImportError:
    MYSQL = False

from .Connector import Connector


class mysqlConnector(Connector):
    db_type = 'mysql'
    replace_char = '%s'
    cursor_args = {"dictionary": True}

    def __init__(self, **dbopts):
        super().__init__(**dbopts)

        if not MYSQL:
            raise ImportError("No MySQL connector available in your system, please install MySQL.")

        self.conn = mysql.connector.connect(**dbopts)

    def upsert(self, table, constraint, cursor=None, **values):
        """
        Insert or on conflict update.
        Ignores the provided constraint.
        """
        valuedict = values
        keys, values = zip(*values.items())

        key_str = self.format_insertkeys(keys)
        value_str, values = self.format_insertvalues(values)
        update_key_str, update_key_values = self.format_updatestr(valuedict)

        cursor = cursor or self.conn.cursor(**self.cursor_args)
        cursor.execute(
            'INSERT INTO {} {} VALUES {} ON DUPLICATE KEY UPDATE {}'.format(
                table, key_str, value_str, update_key_str
            ),
            tuple((*values, *update_key_values))
        )
        self.conn.commit()


class sqliteConnector(Connector):
    db_type = 'sqlite'
    replace_char = '?'
    timeout = 20

    def __init__(self, **dbopts):
        super().__init__(**dbopts)

        data_file = dbopts.get("db_file")
        self.conn = sq.connect(data_file, timeout=dbopts.get("timeout", self.timeout))
        self.conn.row_factory = sq.Row

    def upsert(self, table, constraint, cursor=None, **values):
        """
        Insert or on conflict update.
        """
        valuedict = values
        keys, values = zip(*values.items())

        key_str = self.format_insertkeys(keys)
        value_str, values = self.format_insertvalues(values)
        update_key_str, update_key_values = self.format_updatestr(valuedict)

        if not isinstance(constraint, str):
            constraint = ", ".join(constraint)

        cursor = cursor or self.conn.cursor(**self.cursor_args)
        cursor.execute(
            'INSERT INTO {} {} VALUES {} ON CONFLICT({}) DO UPDATE SET {}'.format(
                table, key_str, value_str, constraint, update_key_str
            ),
            tuple((*values, *update_key_values))
        )
        self.conn.commit()

    def create_database(self):
        """
        Create the database from the schema.
        This will of course only work once.
        """
        self.conn.executescript(self.get_schema())
        self.conn.commit()
