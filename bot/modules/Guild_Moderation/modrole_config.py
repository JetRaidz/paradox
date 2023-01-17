from settings import ColumnData, Role, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from wards import guild_admin

from .module import guild_moderation_module as module


# Define the guild setting
@module.guild_setting
class modrole(ColumnData, Role, GuildSetting):
    attr_name = "modrole"
    category = "Moderation"

    read_check = None
    write_check = guild_admin

    name = "modrole"
    desc = "Moderator role, allowing use of moderation tools without guild permissions."

    long_desc = (
        "Most moderation commands (e.g. `ban`, `kick`, ...) require the moderator "
        "to be able to do these actions manually.\n"
        "Having the `modrole` allows a user to use these commands without "
        "needing, for example, the `ban_members` permission themselves.\n"
        "It also allows use of the `purge` command, which normally requires `Manage Guild`."
    )

    _table_interface_name = "guild_modroles"
    _data_column = "roleid"


# Define data schema
schema = tableSchema(
    "guild_modroles",
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('roleid', ColumnType.SNOWFLAKE, primary=False, required=True),
)


# Attach data interface
@module.data_init_task
def attach_modrole_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=True),
        "guild_modroles"
    )
