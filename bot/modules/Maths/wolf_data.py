from settings import GuildSetting, String, ColumnData
from registry import tableInterface, tableSchema, Column, ColumnType

from wards import guild_admin, fail_ward

from .module import maths_module as module


# Create setting interface
@module.guild_setting
class guild_wolfid(ColumnData, String, GuildSetting):
    attr_name = "wolfram_id"
    category = "Misc"

    read_check = fail_ward
    write_check = guild_admin

    name = "wolfram_id"
    desc = "Custom wolfram AppID for `query` command."

    long_desc = (
        "Custom wolfram application license token to run the `query` command.\n"
        "May be used to upgrade Wolfram queries to a different plan.\n"
        "A limited license may be obtained for free "
        "[here](https://products.wolframalpha.com/api/documentation/#obtaining-an-appid).\n"
        "After obtaining, configure this setting with your `AppID`.\n"
        "*Do not expose your AppID to untrusted members.*"
    )

    _maxlen = 20

    _table_interface_name = "guild_wolfram_appid"
    _data_column = "appid"
    _delete_on_none = True


# Define data schema
schema = tableSchema(
    "guild_wolfram_appid",
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('appid', ColumnType.SHORTSTRING)
)


# Attach data interface
@module.data_init_task
def attach_wolf_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=True),
        "guild_wolfram_appid"
    )
