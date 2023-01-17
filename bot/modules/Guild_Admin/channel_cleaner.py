import asyncio
import discord

from cmdClient import Context

from settings import ListData, ChannelList, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from wards import guild_manager

from .module import guild_admin_module as module


# Define setting command
@module.cmd("autoclean",
            desc="Automatic deletion of messages in the current channel.",
            aliases=["cleanch", "autodelete"])
@guild_manager()
async def cmd_autoclean(ctx: Context):
    """
    Usage``:
        {prefix}autoclean
        {prefix}autoclean <delay>
    Description:
        Enables or disables automatic cleaning of the current channel
        with an optional delay.

        When automatic cleaning is enabled, messages sent in the channel
        will be automatically deleted after a certain amount of time
        unless they are pinned.

        This may be used, for example, for self-role or bot command
        channels where messages don't need to be permanent,
        or where an information message should be kept in view.

        This command requires the `manage_guild` permission.
    Arguments::
        delay: Number of seconds before deleting messages (must be less than an hour).
    Examples``:
        {prefix}autoclean
        {prefix}autoclean 60
    """
    # Retrieve cleaned channel setting for this guild
    cleaned_channels = ctx.get_guild_setting.cleaned_channels

    if cleaned_channels.data and ctx.ch.id in cleaned_channels.data:
        # Remove the channel
        cleaned_channels.remove_channel(ctx.ch.id)
        await ctx.reply("This channel will no longer be automatically cleaned.")
    else:
        # Add the channel
        delay = cleaned_channels.default_delay
        if ctx.args:
            if not ctx.args.isdigit():
                return await ctx.error_reply(ctx.format_usage())

            delay = int(ctx.args)
            if not 0 <= delay <= 3600:
                return await ctx.error_reply("Provided `delay` must be less than an hour.")
        cleaned_channels.add_channel(ctx.ch.id, delay=delay)
        await ctx.reply("Messages in this channel will now be "
                        "automatically deleted after `{}` seconds if they are not pinned.".format(delay))


# Define guild setting
@module.guild_setting
class cleaned_channels(ListData, ChannelList, GuildSetting):
    attr_name = "cleaned_channels"
    category = "Guild admin"

    name = "cleaned_channels"
    desc = "List of channels which I auto-clean."

    long_desc = ("Channels where I automatically delete sent messages "
                 "after a configurable period of time. See the `cleanch` command for more details.")

    default_delay = 60

    _table_interface_name = "guild_cleaned_channels"
    _data_column = "channelid"

    def add_channel(self, channelid, delay=None):
        table = self._get_table_interface(self.client)  # type: tableInterface
        table.insert(allow_replace=True, guildid=self.guildid, channelid=channelid, delay=delay)

        # Update cache
        current = self.client.objects['cleaned_guild_channels'].get(self.guildid, {})
        current[channelid] = delay if delay is not None else self.default_delay
        self.client.objects['cleaned_guild_channels'][self.guildid] = current

    def remove_channel(self, channelid):
        table = self._get_table_interface(self.client)  # type: tableInterface
        table.delete_where(channelid=channelid)

        # Update cache
        self.client.objects['cleaned_guild_channels'].get(self.guildid, {}).pop(channelid, None)

    def write(self, **kwargs):
        """
        Adds a write hook to update the cached guild cleaned channels
        This assumes any new channels have the default delay.
        """
        # TODO: We could also read it in again?
        super().write(**kwargs)

        # Update cleaned channel cache for the current guild
        current = self.client.objects['cleaned_guild_channels'].get(self.guildid, {})
        current.update({chid: self.default_delay for chid in self.data if chid not in current})
        to_remove = [chid for chid in current if chid not in self.data]
        for chid in to_remove:
            current.pop(chid)

        self.client.objects['cleaned_guild_channels'][self.guildid] = current

    @classmethod
    def initialise(cls, client):
        """
        Load the autocleaned channels into cache.
        """
        cleaned_channels = {}
        channel_counter = 0

        rows = client.data.guild_cleaned_channels.select_where()
        for row in rows:
            if row['guildid'] not in cleaned_channels:
                cleaned_channels[row['guildid']] = {}
            cleaned_channels[row['guildid']][row['channelid']] = row['delay']
            channel_counter += 1

        client.objects['cleaned_guild_channels'] = cleaned_channels
        client.log("Read {} guilds with a total of {} autocleaned channels.".format(
            len(cleaned_channels),
            channel_counter),
            context="LOAD_CLEANED_CHANNELS"
        )


# Define event handler
async def autoclean_channel(client, message):
    if message.guild:
        channels = client.objects['cleaned_guild_channels'].get(message.guild.id, None)
        if channels is not None:
            delay = channels.get(message.channel.id, None)
            if delay is not None:
                await asyncio.sleep(delay)
                if not message.pinned:
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        pass
                    except discord.NotFound:
                        pass


@module.init_task
def attach_channel_cleaner(client):
    client.add_after_event('message', autoclean_channel)


# Define data schema
schema = tableSchema(
    "guild_cleaned_channels",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('channelid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('delay', ColumnType.INT, required=True, default=cleaned_channels.default_delay)
)


# Attach data interface
@module.data_init_task
def attach_cleanedchannel_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=False),
        "guild_cleaned_channels"
    )
