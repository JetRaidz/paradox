from settings import ColumnData, Channel, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from wards import guild_admin

from .module import guild_moderation_module as module


# Define the guild setting
@module.guild_setting
class modlog(ColumnData, Channel, GuildSetting):
    attr_name = "modlog"
    category = "Moderation"

    read_check = None
    write_check = guild_admin

    name = "modlog"
    desc = "Channel to post moderation tickets in."

    long_desc = (
        "Channel to post moderation tickets produced by manual moderation commands "
        "(e.g. `ban`, `kick`, `mute`, etc.).\n"
        "See `help tickets` for more information."
    )

    _table_interface_name = "guild_modlogs"
    _data_column = "channelid"


# Define data schema
schema = tableSchema(
    "guild_modlogs",
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('channelid', ColumnType.SNOWFLAKE, primary=False, required=True),
)


# Attach data interface
@module.data_init_task
def attach_modlog_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=True),
        "guild_modlogs"
    )
