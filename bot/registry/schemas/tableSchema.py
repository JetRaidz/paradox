from .elements import Column, ColumnType, ForeignKey, Index, RawElement


class tableSchema:
    """
    Helper to generate a mysql and sqlite schema for a simple table design.

    Parameters
    ----------
    table_name: str
        Name of the table to generate the schema for.
    columns: List[Column]
        List of Columns to add to the schema.
    add_timestamp: bool
        Whether to automatically add a `_timestamp` column with the insert timestamp.
        On mysql this column also updates on update.
    add_app: bool
        Whether to automatically add an `app` column for the current app.

    Returns: Tuple[str, str, Tuple[Tuple[str, type]]]
        Represents `(mysql_schema, sqlite_schema, column_data)`
        where `column_data` is that accepted by `tableManipulator`.
    """
    mysql_formatstr = "CREATE TABLE {table}(\n\t{col_str}{primary_str}{foreign_str}\n);{index_str}{raw_str}"
    sqlite_formatstr = "CREATE TABLE {table}(\n\t{col_str}{primary_str}{foreign_str}\n);{index_str}{raw_str}"

    def __init__(self, table_name, *elements, add_timestamp=True, add_app=False):
        self.name = table_name

        self.columns = []
        self.foreign_keys = []
        self.indexes = []
        self.raws = []
        for element in elements:
            element.table = self.name
            if isinstance(element, Column):
                self.columns.append(element)
            elif isinstance(element, ForeignKey):
                self.foreign_keys.append(element)
            elif isinstance(element, Index):
                self.indexes.append(element)
            elif isinstance(element, RawElement):
                self.raws.append(element)

        if add_app:
            self.columns.append(Column('app', ColumnType.SHORTSTRING, primary=True, required=True))
        if add_timestamp:
            self.columns.append(self.timestamp_column('_timestamp'))

    @property
    def for_mysql(self):
        primary_keys = ','.join(column.name for column in self.columns if column.primary)
        foreign_keys = ',\n\t'.join(foreign_key.for_mysql for foreign_key in self.foreign_keys)
        indexes = '\n'.join(index.for_mysql for index in self.indexes)
        raws = ',\n\t'.join(raw.for_mysql for raw in self.raws)

        return self.mysql_formatstr.format(
            table=self.name,
            col_str=',\n\t'.join(column.for_mysql for column in self.columns),
            primary_str=",\n\tPRIMARY KEY ({})".format(primary_keys) if primary_keys else "",
            foreign_str=',\n\t' + foreign_keys if foreign_keys else "",
            index_str='\n' + indexes if indexes else "",
            raw_str='\n' + raws if raws else ""
        )

    @property
    def for_sqlite(self):
        if not any(column.autoincrement for column in self.columns):
            primary_keys = ','.join(column.name for column in self.columns if column.primary)
        else:
            primary_keys = ""
        foreign_keys = ',\n\t'.join(foreign_key.for_sqlite for foreign_key in self.foreign_keys)
        indexes = '\n'.join(index.for_sqlite for index in self.indexes)
        raws = ',\n\t'.join(raw.for_sqlite for raw in self.raws)

        return self.sqlite_formatstr.format(
            table=self.name,
            col_str=',\n\t'.join(column.for_sqlite for column in self.columns),
            primary_str=",\n\tPRIMARY KEY ({})".format(primary_keys) if primary_keys else "",
            foreign_str=',\n\t' + foreign_keys if foreign_keys else "",
            index_str='\n' + indexes if indexes else "",
            raw_str='\n' + raws if raws else ""
        )

    @property
    def interface_columns(self):
        return tuple(((c.name, c.col_type.pytype) for c in self.columns))

    @staticmethod
    def timestamp_column(name, required=False):
        """
        Quick helper to generate an automatic timestamp column.
        """
        return Column(
            name,
            ColumnType.TIMESTAMP,
            required=required,
            default="CURRENT_TIMESTAMP",
            mysql_update_timestamp=True
        )


def schema_generator(table_name, *columns, add_timestamp=True, add_app=False):
    """
    Helper to generate a mysql and sqlite schema for a simple table design.
    [Deprecated, will be removed in the next version]

    Parameters
    ----------
    table_name: str
        Name of the table to generate the schema for.
    columns: List[Column]
        List of Columns to add to the schema.
    add_timestamp: bool
        Whether to automatically add a `_timestamp` column with the insert timestamp.
        On mysql this column also updates on update.
    add_app: bool
        Whether to automatically add an `app` column for the current app.

    Returns: Tuple[str, str, Tuple[Tuple[str, type]]]
        Represents `(mysql_schema, sqlite_schema, column_data)`
        where `column_data` is that accepted by `tableManipulator`.
    """
    if add_timestamp:
        columns = (*columns, tableSchema.timestamp_column('_timestamp'))
    if add_app:
        columns = (*columns, Column('app', ColumnType.SHORTSTRING, primary=True, required=True))

    table_formatstr = "CREATE TABLE {table}(\n\t{col_strs}{primary_str}\n);"

    primary_keys = ','.join(column.name for column in columns if column.primary)
    primary_key_str = ",\n\tPRIMARY KEY ({})".format(primary_keys) if primary_keys else ""

    # Generate mysql schema
    mysql_col_strs = ',\n\t'.join(column.for_mysql for column in columns)
    mysql_schema = table_formatstr.format(
        table=table_name,
        col_strs=mysql_col_strs,
        primary_str=primary_key_str
    )

    # Generate sqlite schema
    sqlite_col_strs = ',\n\t'.join(column.for_sqlite for column in columns)
    sqlite_schema = table_formatstr.format(
        table=table_name,
        col_strs=sqlite_col_strs,
        primary_str=primary_key_str
    )

    # Generate column data
    column_tuple = tuple(((c.name, c.col_type.pytype) for c in columns))

    return (mysql_schema, sqlite_schema, column_tuple)
