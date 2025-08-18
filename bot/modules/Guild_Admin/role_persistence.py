import logging
import discord

from cmdClient.lib import UserCancelled

from settings import GuildSetting, Boolean, RoleList, ListData, BoolData
from registry import tableInterface, tableSchema, Column, ColumnType
from logging import log

from utils.interactive import ask  # noqa

from wards import guild_admin, guild_manager

from .module import guild_admin_module as module


@module.cmd("forgetrolesfor",
            desc="Forget stored persistent roles for one or all members.",
            flags=['all'])
@guild_admin()
async def cmd_forgetrolesfor(ctx, flags):
    """
    Usage``:
        {prefix}forgetrolesfor <userid>
        {prefix}forgetrolesfor --all
    Description:
        Forgets the persistent roles stored for the given user, or all users.
    Arguments::
        userid: The numerical id of the user to forget.
    Flags::
        all: Forget stored roles for all users.
    """
    if flags['all']:
        # Confirm deletion of all stored persistent roles
        if await ctx.ask("Are you sure you want me to forget all the stored persistent roles for this guild?"):
            # Delete all stored persistent roles
            ctx.client.data.member_stored_roles.delete_where(guildid=ctx.guild.id)
            await ctx.reply("Purged stored persistent roles for all users.")
        else:
            raise UserCancelled("Cancelled upon user request.")
    elif ctx.args:
        # Deleting stored roles for a single user
        if not ctx.args.isdigit():
            return await ctx.error_reply("Please supply the id of the user to forget.")
        else:
            # Lookup the user
            user = await ctx.client.fetch_user(ctx.args)

            if not user:
                return await ctx.error_reply("User `{}` is not known to Discord.".format(ctx.args))
            else:
                ctx.client.data.member_stored_roles.delete_where(guildid=ctx.guild.id, userid=user.id)
                await ctx.reply("Purged stored persistent roles for {} (uid:`{}`).".format(user, user.id))
    else:
        await ctx.reply("Please see the help for this command for usage.")


# Define configuration settings

# Define configuration setting role_persistence (bool, enabled/disabled)
@module.guild_setting
class role_persistence(BoolData, Boolean, GuildSetting):
    attr_name = "role_persistence"
    category = "Moderation"
    read_check = None
    write_check = guild_manager

    name = "role_persistence"
    desc = "Whether roles will be given back to members who re-join."

    long_desc = ("Whether roles will be stored when a member leaves and given back when the member rejoins. "
                 "Any roles in the setting `role_persistence_ignores` will not be returned to them, "
                 "and users may be forgotten with the command `forgetrolesfor`.")

    _outputs = {True: "Enabled",
                False: "Disabled"}

    _default = False

    _table_interface_name = "guild_role_persistence"


# Define configuration setting role_persistence_ignores (Role list)
@module.guild_setting
class role_persistence_ignores(ListData, RoleList, GuildSetting):
    attr_name = "role_persistence_ignores"
    category = "Moderation"
    read_check = None
    write_check = guild_manager

    name = "role_persistence_ignores"
    desc = "List of roles ignored by role persistence."

    long_desc = "Roles which will not be given back to a member when they rejoin, even if they had them when they left."

    _table_interface_name = "guild_role_persistence_ignores"
    _data_column = "roleid"


# Define event handlers
async def store_roles(client, payload):
    """
    Store member roles when the member leaves.
    """
    member = payload.user

    # Collect a list of member roles
    role_list = []
    if isinstance(member, discord.Member):
        role_list = [role.id for role in member.roles]

        # Don't update if the member joined in the last 10 seconds, to allow time for autoroles and role addition
        if discord.utils.utcnow().timestamp() - member.joined_at.timestamp() < 10:
            return

    # Delete the stored roles associated to this member
    client.data.member_stored_roles.delete_where(guildid=payload.guild_id, userid=member.id)
    # TODO: This is asking for some nasty clashes between different apps
    # We probably want to make it a db transaction, i.e. lock the table.

    # Insert the new roles if there are any
    if role_list:
        try:
            client.data.member_stored_roles.insert_many(
                *((payload.guild_id, member.id, role) for role in role_list),
                insert_keys=('guildid', 'userid', 'roleid')
            )
        except Exception:
            pass


async def restore_roles(client, member):
    """
    Restore member roles when a member rejoins.
    """
    if not client.guild_config.role_persistence.get(client, member.guild.id).value:
        # Return if role persistence is not enabled
        return

    # TODO: Also asking for some nasty clashes between different apps, and `autorole` as well.
    # We could place an async lock on role modifications for the user

    # Retrieve the stored roles for this member
    roles = client.data.member_stored_roles.select_where(guildid=member.guild.id, userid=member.id)
    roleids = []
    for i in range(len(roles)):
        roleids.append(roles[i]["roleid"])

    if roleids:
        # Get the ignored roles
        ignored = set(client.guild_config.role_persistence_ignores.get(client, member.guild.id).value)
        # Filter the roles
        roleids = [roleid for roleid in roleids if roleid not in ignored and roleid != member.guild.default_role.id]

    if roleids and member.guild.me.guild_permissions.manage_roles:
        # Get the associated roles, removing the nonexistent ones
        roles = [member.guild.get_role(roleid) for roleid in roleids]
        roles = [role for role in roles if role is not None]

        # Retrieve my top role with manage role permissions
        my_mr_roles = [role for role in member.guild.me.roles
                       if role.permissions.manage_roles or role.permissions.administrator]

        # Filter roles based on what I have permission to add
        if my_mr_roles:
            max_mr_role = max(my_mr_roles)
            roles = [role for role in roles if role < max_mr_role]
        else:
            roles = None

        # Add the roles if there are any left
        if roles:
            try:
                await member.add_roles(*roles, reason="Restoring member roles (Role persistence)")
            except Exception as e:
                log("Failed to restore roles for new member '{}' (uid:{}) in guild '{} (gid:{})."
                    " Exception: {}".format(member,
                                            member.id,
                                            member.guild.name,
                                            member.guild.id,
                                            e.__repr__()),
                    context="RESTORE_ROLE",
                    level=logging.WARNING)


@module.init_task
def attach_restore_roles(client):
    client.add_after_event('raw_member_remove', store_roles)
    client.add_after_event('member_join', restore_roles)


# Define data interfaces
role_persistence_schema = tableSchema(
    "guild_role_persistence",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column("guildid", ColumnType.SNOWFLAKE, primary=True, required=True)
)

role_persistence_ignores_schema = tableSchema(
    "guild_role_persistence_ignores",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column("guildid", ColumnType.SNOWFLAKE, primary=True, required=True),
    Column("roleid", ColumnType.SNOWFLAKE, primary=True, required=True)
)

member_stored_roles_schema = tableSchema(
    "member_stored_roles",
    Column("guildid", ColumnType.SNOWFLAKE, primary=True, required=True),
    Column("userid", ColumnType.SNOWFLAKE, primary=True, required=True),
    Column("roleid", ColumnType.SNOWFLAKE, primary=True, required=True)
)


@module.data_init_task
def attach_rolepersistence_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, role_persistence_schema, shared=False),
        "guild_role_persistence"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, role_persistence_ignores_schema, shared=False),
        "guild_role_persistence_ignores"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, member_stored_roles_schema, shared=True),
        "member_stored_roles"
    )
