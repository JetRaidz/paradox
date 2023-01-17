from settings import ColumnData, Role, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from wards import guild_admin

from .module import guild_moderation_module as module


# Define the guild setting
@module.guild_setting
class muterole(ColumnData, Role, GuildSetting):
    attr_name = "muterole"
    category = "Moderation"

    read_check = None
    write_check = guild_admin

    name = "muterole"
    desc = "Permission-limited role given to muted or jail users."

    long_desc = (
        "Role to give and remove with the `mute` and `unmute` commands.\n"
        "In order to use the role, I must have the `manage roles` permission, "
        "in a role above the muterole."
    )

    _table_interface_name = "guild_muteroles"
    _data_column = "roleid"


# Define data schema
schema = tableSchema(
    "guild_muteroles",
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('roleid', ColumnType.SNOWFLAKE, primary=False, required=True),
)


# Attach data interface
@module.data_init_task
def attach_muterole_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=True),
        "guild_muteroles"
    )
