import logging
import discord
from cmdClient import cmdClient

from logger import log
from settings import ListData, RoleList, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from wards import guild_admin

from .module import guild_admin_module as module


# Define guild settings
@module.guild_setting
class autoroles(ListData, RoleList, GuildSetting):
    attr_name = "autoroles"
    category = "Guild admin"
    read_check = None
    write_check = guild_admin

    name = "autoroles"
    desc = "Roles automatically given to new members."

    long_desc = "Roles automatically given to new members when they join the guild."

    _table_interface_name = "guild_autoroles"
    _data_column = "roleid"


@module.guild_setting
class bot_autoroles(ListData, RoleList, GuildSetting):
    attr_name = "bot_autoroles"
    category = "Guild admin"
    read_check = None
    write_check = guild_admin

    name = "bot_autoroles"
    desc = "Roles automatically given to new bots."

    long_desc = "Roles automatically given to new bots when they join the guild."

    _table_interface_name = "guild_bot_autoroles"
    _data_column = "roleid"


# Define event handler
async def give_autoroles(client: cmdClient, member: discord.Member):
    # Get the autoroles from storage
    if member.bot:
        autoroles = client.guild_config.bot_autoroles.get(client, member.guild.id).value
    else:
        autoroles = client.guild_config.autoroles.get(client, member.guild.id).value

    # Add the autoroles, if we can
    if autoroles and member.guild.me.guild_permissions.manage_roles:
        # Retrieve my top role with manage role permissions
        my_mr_roles = [role for role in member.guild.me.roles
                       if role.permissions.manage_roles or role.permissions.administrator]

        # Filter autoroles based on what I have permission to add
        if my_mr_roles:
            max_mr_role = max(my_mr_roles)
            autoroles = [role for role in autoroles if role is not None and role < max_mr_role]
        else:
            autoroles = None

        # Add the roles if there are any left
        if autoroles:
            try:
                await member.add_roles(*autoroles, reason="Adding autoroles")
            except Exception as e:
                log("Failed to add autoroles to new member '{}' (uid:{}) in guild '{} (gid:{})."
                    " Exception: {}".format(member,
                                            member.id,
                                            member.guild.name,
                                            member.guild.id,
                                            e.__repr__()),
                    context="GIVE_AUTOROLE",
                    level=logging.WARNING)


# Register event handler
@module.init_task
def attach_autorole_handler(client: cmdClient):
    client.add_after_event("member_join", give_autoroles)


# Define data schemas
ar_schema = tableSchema(
    "guild_autoroles",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('roleid', ColumnType.SNOWFLAKE, primary=True, required=True)
)

bar_schema = tableSchema(
    "guild_bot_autoroles",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('roleid', ColumnType.SNOWFLAKE, primary=True, required=True)
)


# Attach data interfaces
@module.data_init_task
def attach_autorole_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, ar_schema, shared=False),
        "guild_autoroles"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, bar_schema, shared=False),
        "guild_bot_autoroles"
    )
