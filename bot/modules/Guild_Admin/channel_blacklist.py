from settings import ListData, ChannelList, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from .module import guild_admin_module as module

from wards import guild_manager


# Define guild settings
@module.guild_setting
class disabled_channels(ListData, ChannelList, GuildSetting):
    attr_name = "disabled_channels"
    category = "Guild admin"
    read_check = None
    write_check = guild_manager

    name = "disabled_channels"
    desc = "List of channels where I don't listen to commands."

    long_desc = ("List of channels where I only respond to commands sent by a guild administrator.\n"
                 "This does not affect LaTeX rendering. Use the `latex_channels` config to "
                 "restrict where automatic LaTeX compilation may occur.")

    _table_interface_name = "guild_disabled_channels"
    _data_column = "channelid"

    def write(self, **kwargs):
        """
        Adds a write hook to update the cached guild disabled channels
        """
        # Update cache for this guild
        self.client.objects['disabled_guild_channels'][self.guildid] = set(self.data)
        super().write(**kwargs)

    @classmethod
    def initialise(cls, client):
        """
        Load the disabled channels into cache.
        """
        disabled_channels = {}
        channel_counter = 0

        rows = client.data.guild_disabled_channels.select_where()
        for row in rows:
            if row['guildid'] not in disabled_channels:
                disabled_channels[row['guildid']] = set()
            disabled_channels[row['guildid']].add(row['channelid'])
            channel_counter += 1

        client.objects['disabled_guild_channels'] = disabled_channels
        client.log("Read {} guilds with a total of {} disabled channels.".format(
            len(disabled_channels),
            channel_counter),
            context="LOAD_DISABLED_CHANNELS"
        )


# Define data schema
schema = tableSchema(
    "guild_disabled_channels",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('channelid', ColumnType.SNOWFLAKE, primary=True, required=True)
)


# Attach data interface
@module.data_init_task
def attach_disabled_channel_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=False),
        "guild_disabled_channels"
    )
