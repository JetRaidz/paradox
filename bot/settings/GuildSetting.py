from typing import Any
import discord

from cmdClient import cmdClient, Context
from cmdClient.Check import Check

from utils.lib import prop_tabulate


class GuildSetting:
    """
    Abstract base class describing a guild configuration setting.
    A setting consists of logic to load the setting from storage,
    present it in a readable form, understand user entered values,
    and write it again in storage.
    Additionally, the setting has attributes attached describing
    the setting in a user-friendly manner for display purposes.
    """
    attr_name: str = None  # Internal name for the setting
    _default: Any = None  # Default data value for the setting.. this may be None if the setting overrides 'default'.

    # Read and write checks.
    # These are not guaranteed to be checked internally, and should be handled by the caller
    read_check: Check = None  # Check that needs to be passed to read the setting
    write_check: Check = None  # Check that needs to be passed before changing the setting

    # Configuration interface descriptions
    hidden: bool = False  # Whether this setting should appear in the configuration
    category: str = None  # The name of the category this setting belongs to

    name: str = None  # User readable name of the setting
    desc: str = None  # User readable brief description of the setting
    long_desc: str = None  # User readable long description of the setting
    accepts: str = None  # User readable description of the acceptable values

    def __init__(self, client: cmdClient, guildid: id, data: Any, **kwargs):
        self.client = client
        self.guildid = guildid
        self._data = data

    # Configuration embeds
    @property
    def embed(self):
        """
        Discord Embed showing an information summary about the setting.
        """
        embed = discord.Embed(
            title="Configuration options for `{}`".format(self.name),
        )
        fields = ("Current value", "Default value", "Accepted input")
        values = (self.formatted or "Not Set",
                  self._format_data(self.client, self.guildid, self.default) or "None",
                  self.accepts)
        table = prop_tabulate(fields, values)
        embed.description = "{}\n{}".format(self.long_desc, table)
        return embed

    @property
    def hidden_embed(self):
        """
        Discord Embed showing an information summary about the setting, shown when `read_check` fails.
        """
        embed = discord.Embed(
            title="Configuration options for `{}`".format(self.name),
        )
        fields = ("Current value", "Default value", "Accepted input")
        values = ("Hidden",
                  self._format_data(self.client, self.guildid, self.default) or "None",
                  self.accepts)
        table = prop_tabulate(fields, values)
        embed.description = "{}\n{}".format(self.long_desc, table)
        return embed

    # Instance generation
    @classmethod
    def get(cls, client: cmdClient, guildid: int, **kwargs):
        """
        Return a setting instance initialised from the stored value.
        """
        data = cls._reader(client, guildid, **kwargs)
        return cls(client, guildid, data, **kwargs)

    @classmethod
    async def parse(cls, ctx: Context, userstr: str, **kwargs):
        """
        Return a setting instance initialised from a parsed user string.
        """
        data = await cls._parse_userstr(ctx, ctx.guild.id, userstr, **kwargs)
        return cls(ctx.client, ctx.guild.id, data, **kwargs)

    # Main interface
    @property
    def data(self):
        """
        Retrieves the current internal setting data if it is set, otherwise the default data
        """
        return self._data if self._data is not None else self.default

    @data.setter
    def data(self, new_data):
        """
        Sets the internal setting data and writes the changes.
        """
        self._data = new_data
        self.write()

    @property
    def default(self):
        """
        Retrieves the default value for this setting.
        Settings should override this if the default depends on the client or guild.
        """
        return self._default

    @property
    def value(self):
        """
        Discord-aware object or objects associated with the setting.
        """
        return self._data_to_value(self.client, self.guildid, self.data)

    @value.setter
    def value(self, new_value):
        """
        Setter which reads the discord-aware object, converts it to data, and writes it.
        """
        self._data = self._data_from_value(self.client, self.guildid, new_value)
        self.write()

    @property
    def formatted(self):
        """
        User-readable form of the setting.
        """
        return self._format_data(self.client, self.guildid, self.data)

    def write(self, **kwargs):
        """
        Write value to the database.
        For settings which override this,
        ensure you handle deletion of values when internal data is None.
        """
        self._writer(self.client, self.guildid, self._data, **kwargs)

    # Raw converters
    @classmethod
    def _data_from_value(cls, client: cmdClient, guildid: int, value, **kwargs):
        """
        Convert a high-level setting value to internal data.
        Must be overriden by the setting.
        Be aware of None values, these should always pass through as None
        to provide an unsetting interface.
        """
        raise NotImplementedError

    @classmethod
    def _data_to_value(cls, client: cmdClient, guildid: int, data: Any, **kwargs):
        """
        Convert internal data to high-level setting value.
        Must be overriden by the setting.
        """
        raise NotImplementedError

    @classmethod
    async def _parse_userstr(cls, ctx: Context, guildid: int, userstr: str, **kwargs):
        """
        Parse user provided input into internal data.
        Must be overriden by the setting if the setting is user-configurable.
        """
        raise NotImplementedError

    @classmethod
    def _format_data(cls, client: cmdClient, guildid: int, data: Any, **kwargs):
        """
        Convert internal data into a formatted user-readable string.
        Must be overriden by the setting if the setting is user-viewable.
        """
        raise NotImplementedError

    # Database access classmethods
    @classmethod
    def _reader(cls, client: cmdClient, guildid: int, **kwargs):
        """
        Read a setting from storage and return setting data or None.
        Must be overriden by the setting.
        """
        raise NotImplementedError

    @classmethod
    def _writer(cls, client: cmdClient, guildid: int, data: Any, **kwargs):
        """
        Write provided setting data to storage.
        Must be overriden by the setting unless the `write` method is overidden.
        If the data is None, the setting is empty and should be unset.
        """
        raise NotImplementedError

    # Helper methods for external use
    @classmethod
    def initialise(cls, client: cmdClient, **kwargs):
        """
        Initialisation method to set up the client for this setting.
        The setting does not run this itself,
        but may assume this has been run before instantiation.
        """
        pass
