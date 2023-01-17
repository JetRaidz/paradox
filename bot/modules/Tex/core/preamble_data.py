from registry import tableSchema, Column, ColumnType, tableInterface

from ..module import latex_module as module


# The active user and guild preambles
user_preamble_schema = tableSchema(
    "user_latex_preambles",
    Column('userid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('preamble', ColumnType.TEXT, primary=False, required=False),
    Column('previous_preamble', ColumnType.TEXT, primary=False, required=False),
    Column('whitelisted', ColumnType.BOOL, primary=False, required=False),
)

guild_preamble_schema = tableSchema(
    "guild_latex_preambles",
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('preamble', ColumnType.TEXT, primary=False, required=True),
)

# The pending preambles
user_pending_preamble_schema = tableSchema(
    "user_pending_preambles",
    Column('userid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('app', ColumnType.SHORTSTRING, required=True),
    Column('username', ColumnType.SHORTSTRING, required=True),
    Column('pending_preamble', ColumnType.TEXT, required=True),
    Column('pending_preamble_diff', ColumnType.TEXT, required=False),
    Column('submission_time', ColumnType.INT, required=True),
    Column('submission_message_id', ColumnType.SNOWFLAKE, required=False),
    Column('submission_summary', ColumnType.MSGSTRING, required=True),
    Column('submission_source_id', ColumnType.SNOWFLAKE, required=True),
    Column('submission_source_name', ColumnType.SHORTSTRING, required=True),
)

# Global data
global_preset_schema = tableSchema(
    "global_latex_presets",
    Column('name', ColumnType.SHORTSTRING, required=True),
    Column('preset', ColumnType.TEXT, required=True),
)

global_whitelist_schema = tableSchema(
    "global_latex_package_whitelist",
    Column('package', ColumnType.SHORTSTRING, required=True),
)


# Attach data interfaces
@module.data_init_task
def attach_preamble_data(client):
    # User active preambles
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, user_preamble_schema, shared=True),
        "user_latex_preambles"
    )

    # Guild active preambles
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, guild_preamble_schema, shared=True),
        "guild_latex_preambles"
    )

    # User pending preambles
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, user_pending_preamble_schema, shared=True),
        "user_pending_preambles"
    )

    # Global presets
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, global_preset_schema, shared=True),
        "global_latex_presets"
    )

    # Global package whitelist
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, global_whitelist_schema, shared=True),
        "global_package_whitelist"
    )
