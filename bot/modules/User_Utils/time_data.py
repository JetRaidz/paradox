from registry import tableSchema, Column, ColumnType, tableInterface

from .module import utils_module as module


schema = tableSchema(
    "user_time_settings",
    Column('userid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('timezone', ColumnType.SHORTSTRING),
    Column('brief_display', ColumnType.BOOL, default=False),
)


# Attach data interfaces
@module.data_init_task
def attach_time_settings_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=True),
        "user_time_settings"
    )
