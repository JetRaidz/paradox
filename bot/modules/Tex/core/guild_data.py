from registry import tableSchema, Column, ColumnType, tableInterface

from ..module import latex_module as module

from . import preamble_data  # noqa


# Define data schema
config_schema = tableSchema(
    "guild_latex_config",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('autotex', ColumnType.BOOL, primary=False, required=False),
    Column('autotex_level', ColumnType.INT, primary=False, required=False),
    Column('require_codeblocks', ColumnType.BOOL, primary=False, required=False),
)

channel_schema = tableSchema(
    "guild_latex_channels",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('channelid', ColumnType.SNOWFLAKE, primary=True, required=True),
)


# Attach data interfaces
@module.data_init_task
def attach_latexguild_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, config_schema, shared=False),
        "guild_latex_config"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, channel_schema, shared=False),
        "guild_latex_channels"
    )
