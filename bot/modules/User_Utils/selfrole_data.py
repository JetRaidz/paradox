from settings import ListData, RoleList, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from wards import guild_admin

from .module import utils_module as module


# Define guild settings
@module.guild_setting
class selfroles(ListData, RoleList, GuildSetting):
    attr_name = "selfroles"
    category = "Guild admin"
    read_check = None
    write_check = guild_admin

    name = "selfroles"
    desc = "Roles that members may assign themselves via the `selfrole` command."

    long_desc = (
        "A list of roles that members may assign themselves via the `selfrole` command.\n"
        "Roles may also be individually added or removed with the `selfrole` command.\n"
        "See `help selfroles` for more information."
    )

    _table_interface_name = "guild_selfroles"
    _data_column = "roleid"


# Define data schema
schema = tableSchema(
    "guild_selfroles",
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('roleid', ColumnType.SNOWFLAKE, primary=True, required=True)
)


# Attach data interfaces
@module.data_init_task
def attach_selfrole_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=True),
        "guild_selfroles"
    )
