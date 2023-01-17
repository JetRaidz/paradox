import logging
import asyncio
from datetime import datetime
from enum import Enum

import discord

from settings import GuildSetting, SettingList, Channel, MemberList, IntegerEnum, ColumnData, ListData
from registry import tableInterface, tableSchema, Column, ColumnType

from wards import guild_manager
from utils.lib import prop_tabulate

from .module import guild_logging_module as module


class UserLogEvent(Enum):
    USERNAME = 0
    NICKNAME = 1
    AVATAR = 2
    ROLES = 3


async def member_update_handler(client, before, after, from_user=False, guild=None):
    # Check the event is one we we can handle
    if not (before.name != after.name
            or (not from_user and before.nick != after.nick)
            or before.avatar_url != after.avatar_url
            or (not from_user and before.roles != after.roles)):
        return

    # Get the various guild settings, with appropriate return conditions
    guild = after.guild if not from_user else guild
    userlog = client.guild_config.userlog.get(client, guild.id).value
    if not userlog:
        return

    userlog_events = client.guild_config.userlog_events.get(client, guild.id).value
    if not userlog_events:
        return

    userlog_ignore = client.guild_config.userlog_ignores.get(client, guild.id).value
    if userlog_ignore and before in userlog_ignore:
        return

    # Build the description
    desc_lines = []
    image = None

    if before.name != after.name and UserLogEvent.USERNAME in userlog_events:
        # Handle name changes
        desc_lines.append(
            "**Username updated!**\n"
            "`Before:` {}\n"
            "`After:` {}\n".format(before.name, after.name)
        )

    if not from_user and before.nick != after.nick and UserLogEvent.NICKNAME in userlog_events:
        # Handle nickname changes
        desc_lines.append(
            "**Nickname updated!**\n"
            "`Before:` {}\n"
            "`After:` {}\n".format(before.nick, after.nick)
        )

    if before.avatar_url != after.avatar_url and UserLogEvent.AVATAR in userlog_events:
        # Handle avatar changes
        desc_lines.append(
            "**Avatar updated!**\n"
            "`Before:` [Old Avatar]({})\n"
            "`After:` [New Avatar]({})\n".format(before.avatar_url, after.avatar_url)
        )
        image = after.avatar_url if after.avatar_url else None

    if not from_user and before.roles != after.roles and UserLogEvent.ROLES in userlog_events:
        # Handle role changes
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        desc_lines.append("**Roles updated!**")
        if added_roles:
            desc_lines.append("Added roles {}".format(", ".join(r.mention for r in added_roles)))
        if removed_roles:
            desc_lines.append("Removed roles {}".format(", ".join(r.mention for r in removed_roles)))

    # Return if we have somehow ended up with an empty description
    if not desc_lines:
        return

    # Build log embed
    description = "{}\n{}".format(after.mention, "\n".join(desc_lines))
    colour = (after.colour if after.colour.value else discord.Colour.light_grey())

    embed = discord.Embed(color=colour, description=description, timestamp=datetime.now())
    embed.set_author(
        name="{} ({})".format(after, after.id)
    )
    if image is not None:
        embed.set_thumbnail(url=image)

    # Finally, send the embed
    try:
        await userlog.send(embed=embed)
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass
    except Exception as e:
        client.log("Failed to post user update log for member '{}' (uid:{}) in guild '{} (gid:{})."
                   " Exception: {}".format(after,
                                           after.id,
                                           after.guild.name,
                                           after.guild.id,
                                           e.__repr__()),
                   context="POST_USERLOG",
                   level=logging.WARNING)


async def user_update_handler(client, before, after):
    # Check the event is one we we can handle
    if not (before.name != after.name
            or before.avatar_url != after.avatar_url):
        return
    # Get the shared guilds
    guilds = [g for g in client.guilds if after in g.members]

    for guild in guilds:
        asyncio.ensure_future(member_update_handler(client, before, after, from_user=True, guild=guild))


@module.init_task
def attach_userlog_handler(client):
    # client.add_after_event("member_update", member_update_handler)
    # client.add_after_event("user_update", user_update_handler)
    pass


# Define guild configuration settings
@module.guild_setting
class guild_userlog(ColumnData, Channel, GuildSetting):
    attr_name = "userlog"
    category = "Logging"
    read_check = None
    write_check = guild_manager

    name = "userlog"
    desc = "Channel to log user and member metainfo updates."

    long_desc = (
        "Channel to log member and user updates, for example avatar, name, and role updates.\n"
        "See the `userlog_events` setting for the loggable events, "
        "and the `userlog_ignores` setting to ignore specific users."
    )

    _table_interface_name = "guild_userupdate_channel"
    _data_column = "channelid"
    _delete_on_none = True


@module.guild_setting
class guild_userlog_ignores(ListData, MemberList, GuildSetting):
    attr_name = "userlog_ignores"
    category = "Logging"
    read_check = None
    write_check = guild_manager

    name = "userlog_ignores"
    desc = "The users to ignore in the userlog."

    long_desc = (
        "Users listed in this setting will not be shown in the userlog.\n"
        "This may be useful to e.g. ignore continuously updating bot avatars."
    )

    _table_interface_name = "guild_userupdate_ignores"
    _data_column = "userid"


class _userlog_event(IntegerEnum):
    _enum = UserLogEvent

    _output_map = {
        UserLogEvent.USERNAME: "Username",
        UserLogEvent.NICKNAME: "Nickname",
        UserLogEvent.AVATAR: "Avatar",
        UserLogEvent.ROLES: "Roles"
    }


@module.guild_setting
class guild_userlog_events(ListData, SettingList, GuildSetting):
    attr_name = "userlog_events"
    category = "Logging"
    read_check = None
    write_check = guild_manager

    name = "userlog_events"
    desc = "The event types to log in the userlog."
    long_desc = (
        "The event types to be logged into the userlog."
    )

    accepts = "Comma separated list of userlog event types (listed below)."
    _setting = _userlog_event
    _force_unique = True

    _default = [0, 1, 2, 3]
    _table_interface_name = "guild_userupdate_events"
    _data_column = "event"

    @property
    def embed(self):
        embed = super().embed
        event_types = {
            "Username": "Updates to a member's global username.",
            "Avatar": "Updates to a member's global avatar.",
            "Nickname": "Updates to a member's guild nickname.",
            "Roles": "New or removed roles for a member.",
        }
        table = prop_tabulate(*zip(*event_types.items()))
        embed.add_field(
            name="Userlog Event types",
            value=table
        )
        return embed


# Define data schemas
channel_schema = tableSchema(
    "guild_userupdate_channel",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('channelid', ColumnType.SNOWFLAKE),  # Channel to log the userupdates to
)

event_schema = tableSchema(
    "guild_userupdate_events",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('event', ColumnType.INT, primary=True, required=True),  # The event types to log
)

ignores_schema = tableSchema(
    "guild_userupdate_ignores",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('userid', ColumnType.SNOWFLAKE, primary=True, required=True),
)


# Attach data interfaces
@module.data_init_task
def attach_userlog_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, channel_schema, shared=False),
        "guild_userupdate_channel"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, event_schema, shared=False),
        "guild_userupdate_events"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, ignores_schema, shared=False),
        "guild_userupdate_ignores"
    )
