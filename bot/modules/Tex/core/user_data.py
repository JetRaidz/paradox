from registry import tableSchema, Column, ColumnType, tableInterface

from ..module import latex_module as module

from . import preamble_data  # noqa


# Define data schema
config_schema = tableSchema(
    "user_latex_config",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('userid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('autotex', ColumnType.BOOL, primary=False, required=False),
    Column('keepsourcefor', ColumnType.INT, primary=False, required=False),
    Column('colour', ColumnType.SHORTSTRING, primary=False, required=False),
    Column('alwaysmath', ColumnType.BOOL, primary=False, required=False),
    Column('alwayswide', ColumnType.BOOL, primary=False, required=False),
    Column('namestyle', ColumnType.INT, primary=False, required=False),
    Column('autotex_level', ColumnType.INT, primary=False, required=False),
)


# Attach data interfaces
@module.data_init_task
def attach_latexguild_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, config_schema, shared=False),
        "user_latex_config"
    )
