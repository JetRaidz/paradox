from typing import Optional
import logging
import asyncio
import re

import discord

from settings import ColumnData, ListData, String, Integer, Channel, RoleList, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from wards import guild_manager

from utils.lib import shard_of

from paraModule import paraModule

module = paraModule(
    "Starboard",
    description="React to messages to add them to a central starboard channel."
)


class _Starboard:
    """
    Simple slotted class representing a guild with active starboard.
    """
    starboards = {}  # Global starboard cache

    _slots = ('guildid', 'channelid', 'emoji', 'threshold', 'lock')

    def __init__(self, guildid: int, channelid: int, emoji: Optional[str] = None, threshold: Optional[int] = None):
        self.guildid = guildid
        self.channelid = channelid
        self.emoji = emoji
        self.threshold = threshold

        self.lock = asyncio.Lock()


# Guild configuration
@module.guild_setting
class starboard(ColumnData, Channel, GuildSetting):
    attr_name = "starboard"
    category = "Starboard"
    read_check = None
    write_check = guild_manager

    name = "starboard"
    desc = "Channel to post starred messages"

    long_desc = ("The starboard channel acts as a global pinboard.\n"
                 "To save message on the starboard, members may star messages by "
                 "reacting with the `star_emoji`, usually ⭐.\n"
                 "See the `star_emoji`, `star_threshold` and `star_roles` settings for further configuration.")

    _table_interface_name = "guild_starboards"
    _data_column = "channelid"
    _delete_on_none = False

    def write(self, **kwargs):
        """
        Adds a write hook to update the cached guild starboard.
        """
        super().write(**kwargs)
        starboards = _Starboard.starboards
        if self.data is not None:
            starboard = starboards.get(self.guildid, None)
            if starboard is not None:
                starboard.channelid = self.data
            else:
                row = self.client.data.guild_starboards.select_one_where(guildid=self.guildid)
                if row is not None:
                    starboards[self.guildid] = _Starboard(
                        self.guildid,
                        self.data,
                        row['emoji'],
                        row['threshold']
                    )
        else:
            starboards.pop(self.guildid, None)

    @classmethod
    def _reader(cls, client, guildid, **kwargs):
        """
        Read the starboard channel from cache.
        """
        starboard = _Starboard.starboards.get(guildid, None)
        return starboard.channelid if starboard is not None else None

    @classmethod
    def initialise(cls, client):
        """
        Load the guilds with starboards
        """
        starboards = {}

        rows = client.data.guild_starboards.select_where()
        for row in rows:
            gid = row['guildid']
            if row['channelid'] and shard_of(client.shard_count, gid) == client.shard_id:
                starboards[gid] = _Starboard(gid, row['channelid'], row['emoji'], row['threshold'])

        _Starboard.starboards = starboards
        client.objects['starboards'] = starboards
        client.log("Cached {} starboards!".format(len(starboards)),
                   context="LOAD_STARBOARDS")


@module.guild_setting
class star_emoji(ColumnData, String, GuildSetting):
    attr_name = "star_emoji"
    category = "Starboard"
    read_check = None
    write_check = guild_manager

    name = "star_emoji"
    desc = "Emoji used to star messages."

    long_desc = "React with this emoji to send a message to the `starboard`."

    _default = '⭐'

    _maxlen = 64
    _quote = False

    _table_interface_name = "guild_starboards"
    _data_column = "emoji"
    _delete_on_none = False

    def write(self, **kwargs):
        """
        Adds a write hook to update the cached guild starboard.
        """
        super().write(**kwargs)
        starboards = _Starboard.starboards
        if self.data is not None and self.guildid in starboards:
            starboards[self.guildid].emoji = self.data

    @classmethod
    def _reader(cls, client, guildid, **kwargs):
        """
        Read the starboard emoji from cache.
        """
        starboard = _Starboard.starboards.get(guildid, None)
        return starboard.emoji if starboard is not None else None


@module.guild_setting
class star_threshold(ColumnData, Integer, GuildSetting):
    attr_name = "star_threshold"
    category = "Starboard"
    read_check = None
    write_check = guild_manager

    name = "star_threshold"
    desc = "Number of stars required to star a message."

    long_desc = "The minimum number of stars required before a message will appear on the starboard."

    _default = 1

    _min = 1

    _table_interface_name = "guild_starboards"
    _data_column = "threshold"
    _delete_on_none = False

    def write(self, **kwargs):
        """
        Adds a write hook to update the cached guild starboard.
        """
        super().write(**kwargs)
        starboards = _Starboard.starboards
        if self.data is not None and self.guildid in starboards:
            starboards[self.guildid].threshold = self.data

    @classmethod
    def _reader(cls, client, guildid, **kwargs):
        """
        Read the starboard emoji from cache.
        """
        starboard = _Starboard.starboards.get(guildid, None)
        return starboard.threshold if starboard is not None else None


@module.guild_setting
class starboard_roles(ListData, RoleList, GuildSetting):
    attr_name = "star_roles"
    category = "Starboard"
    read_check = None
    write_check = guild_manager

    name = "star_roles"
    desc = "The roles allowed to star a message."

    long_desc = ("A message must have at least one reaction from a member "
                 "with one of these roles to appear on the starboard.")

    _table_interface_name = "guild_starboard_roles"
    _data_column = "roleid"


async def chunk_guild(client, guild):
    """
    Guild chunking function that is independent of ctx to allow star roles to work as intended.
    """

    # The guild isn't chunked, begin
    if not guild.chunked:

        # Gracefully error if the bot lacks the Members Privileged Intent
        if not client.intents.members:
            client.log(f"Failed to chunk guild {guild.name} ({guild.id}) as the bot lacks Members Privileged Intent.",
                       level=logging.ERROR)
            return False

        task = asyncio.create_task(guild.chunk())
        client.log(f"Function starboard requested guild chunking for {guild.name} ({guild.id}).",
                   level=logging.WARNING)

        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=1)
            # The guild has been chunked successfully!
            client.log(f"{guild.name} ({guild.id}) is now chunked.")

        # Chunking the guild is taking longer than normal, send a message to the author
        except asyncio.TimeoutError:

            try:
                await asyncio.wait_for(task, timeout=10)

            # It has taken 10 seconds and there has been no response
            # Either Discord isn't working or the request was left hanging
            except asyncio.TimeoutError:
                client.log(f"Timed out chunking guild {guild.name} ({guild.id}).",
                           level=logging.WARNING)
                return False

            else:
                # The guild has successfully been chunked but took longer than normal
                client.log(f"{guild.name} ({guild.id}) is now chunked.")
                return True

    # The guild is already chunked, skip the chunking process
    return True


# Event handler
async def starboard_listener(client, payload):
    if not payload.guild_id or payload.guild_id not in _Starboard.starboards:
        # Not in a guild with an active starboard
        return

    # Check that the emoji is correct
    star_emoji = client.guild_config.star_emoji.get(client, payload.guild_id).value

    if payload.emoji.is_unicode_emoji():
        if str(payload.emoji) != star_emoji:
            return
    else:
        eid = star_emoji.strip('<>').rpartition(':')[-1]
        if not eid.isdigit() or not int(eid) == payload.emoji.id:
            return

    # Get the guild starboard and make sure it exists
    starboard = client.guild_config.starboard.get(client, payload.guild_id).value
    if starboard is None:
        return

    # We are in a guild with an active starboard, and have received a star reaction event
    async with _Starboard.starboards[payload.guild_id].lock:
        # Collect the message data
        try:
            message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
            rows = client.data.message_stars.select_where(msgid=payload.message_id)
            starmsg_id = rows[0]['starmsgid'] if rows else None
        except discord.NotFound:
            return
        except discord.Forbidden:
            return

        unstar = False
        # Collect the reaction data
        reaction = next((reaction for reaction in message.reactions
                         if reaction.emoji == payload.emoji or str(reaction.emoji) == str(payload.emoji)), None)
        if reaction is None:
            unstar = True

        # Check the threshold, if set
        if not unstar and reaction.count < client.guild_config.star_threshold.get(client, payload.guild_id).value:
            unstar = True

        # If there are star roles, check them now
        # Probably add these to the cache?
        if not unstar:
            # Disregard stars if message is from the bot and in starboard channel
            if message.channel == starboard and message.author.id == client.user.id:
                return

            roles = client.guild_config.star_roles.get(client, payload.guild_id).value
            if roles:
                # Request chunking so that reaction user roles can be fetched
                if not message.guild.chunked:
                    await chunk_guild(client, message.guild)

                users = [user async for user in reaction.users()]
                if not any(any(role in user.roles for role in roles) for user in users):
                    # None of the reacting users have a star role
                    unstar = True

        if unstar:
            # Remove the message from the starboard, if it exists
            if starmsg_id:
                # Remove the star message
                client.data.message_stars.delete_where(msgid=payload.message_id)

                # Get the star message and delete it if possible
                try:
                    message = await starboard.fetch_message(starmsg_id)
                    await message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
            return

        # The star reaction event passes the guild threshold and star roles
        # Build the starboard message
        header = "{} {} in {}".format(reaction.count, reaction.emoji, message.channel.mention)
        embed = discord.Embed(colour=discord.Colour.gold(),
                              description=message.content,
                              timestamp=message.created_at)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar)
        embed.add_field(name="Message link", value="[Click to jump to message]({})".format(message.jump_url))

        # Check whether the link is marked as a spoiler
        def link_spoiler(text, link):
            regex = r"\|\|(.+?)\|\|"
            spoiler_list = re.findall(regex, text)
            for spoiler in spoiler_list:
                if link in spoiler:
                    return True
            return False

        # If the starred embed has an image, embed it while respecting spoilers
        if message.embeds:
            data = message.embeds[0]

            if data.type == "image" and not link_spoiler(message.content, data.url):
                embed.set_image(url=data.url)

            elif data.type == "image" and link_spoiler(message.content, data.url):
                embed.add_field(name="Attachment", value=f"||[Image (spoiler)]({data.url})||", inline=False)

            else:
                pass

        # If the message has an attachment and it can be displayed, embed it while respecting spoilers
        elif message.attachments:
            data = message.attachments[0]
            filename = data.filename
            spoiler = data.is_spoiler()

            # Split junk from attachment URL
            data_url = data.url.split("?")[0]

            if not spoiler and data_url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=data_url)

            # Link the file if it has a spoiler as images can't be marked as spoilers in embeds
            elif spoiler:
                embed.add_field(name='Attachment', value=f'||[{discord.utils.escape_markdown(filename)}]({data.url})||', inline=False)

            # Link any file that isn't an image
            else:
                embed.add_field(name='Attachment', value=f'[{filename}]({data.url})', inline=False)

        # Send or update the starboard message
        sent = False
        if starmsg_id:
            try:
                starmsg = await starboard.fetch_message(starmsg_id)
                await starmsg.edit(content=header, embed=embed)
                sent = True
            except discord.NotFound:
                pass
            except discord.Forbidden:
                return

        if not sent:
            try:
                starmsg = await starboard.send(content=header, embed=embed)
                client.data.message_stars.insert(allow_replace=True, msgid=message.id, starmsgid=starmsg.id)
            except discord.Forbidden:
                pass
            except discord.NotFound:
                pass


# Attach event
@module.init_task
def attach_starboard_listener(client):
    client.add_after_event('raw_reaction_add', starboard_listener)
    client.add_after_event('raw_reaction_remove', starboard_listener)


# Data schemas
# Guild starboard
starboard_schema = tableSchema(
    "guild_starboards",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('channelid', ColumnType.SNOWFLAKE),
    Column('emoji', ColumnType.SHORTSTRING),
    Column('threshold', ColumnType.INT, required=True, default=1)
)

# Guild starboard roles
starboard_role_schema = tableSchema(
    "guild_starboard_roles",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('roleid', ColumnType.SNOWFLAKE, required=True)
)

# Starboard messages: app, msgid, starmsgid, starcount
starmsg_schema = tableSchema(
    "message_stars",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('msgid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('starmsgid', ColumnType.SNOWFLAKE, required=True),
)


# Attach data interfaces
@module.data_init_task
def attach_starboard_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, starboard_schema, shared=False),
        "guild_starboards"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, starboard_role_schema, shared=False),
        "guild_starboard_roles"
    )

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, starmsg_schema, shared=False),
        "message_stars"
    )
