from registry import tableInterface, Column, ColumnType, tableSchema, ForeignKey, ReferenceAction

from ..module import guild_moderation_module as module


# Define data schemas
ticket_schema = tableSchema(
    "guild_moderation_tickets",
    Column('ticketid', ColumnType.INT, autoincrement=True, primary=True),
    Column('ticket_type', ColumnType.INT, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, required=True),
    Column('modid', ColumnType.SNOWFLAKE, required=True),
    Column('agentid', ColumnType.SNOWFLAKE, required=True),
    Column('app', ColumnType.SHORTSTRING, required=True),
    Column('msgid', ColumnType.SNOWFLAKE, required=False),
    Column('auditid', ColumnType.SNOWFLAKE, required=False),
    Column('reason', ColumnType.MSGSTRING, required=False),
    Column('created_at', ColumnType.INT, required=True),
)

member_schema = tableSchema(
    "guild_moderation_ticket_members",
    Column('ticketid', ColumnType.INT, required=True),
    Column('memberid', ColumnType.SNOWFLAKE, required=True),
    ForeignKey('ticketid', ticket_schema.name, 'ticketid', on_delete=ReferenceAction.CASCADE)
)


# Attach data interfaces
@module.data_init_task
def attach_mod_ticket_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, ticket_schema, shared=True),
        "guild_mod_tickets"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, member_schema, shared=True),
        "guild_mod_ticket_members"
    )
