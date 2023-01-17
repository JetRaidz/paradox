from settings import GuildSetting, Boolean, IntegerEnum, ChannelList, ColumnData, ListData

from wards import guild_manager

from ..module import latex_module as module

from .LatexGuild import LatexGuild
from .tex_utils import AutoTexLevel


@module.guild_setting
class autotex(ColumnData, Boolean, GuildSetting):
    attr_name = "autotex"
    category = "LaTeX"
    read_check = None
    write_check = guild_manager

    name = "latex"
    desc = "Automatically compile LaTeX messages."

    long_desc = ("When enabled, automatically detect and compile LaTeX in messages.\n"
                 "Affected by the other LaTeX guild settings, and personal configuration.")

    _outputs = {True: "Enabled",
                False: "Disabled"}

    _default = LatexGuild.defaults['autotex']

    _table_interface_name = "guild_latex_config"
    _data_column = "autotex"
    _delete_on_none = False

    def write(self, **kwargs):
        """
        Write data and update stored LatexGuild
        """
        super().write(**kwargs)
        LatexGuild.get(self.guildid).load()


@module.guild_setting
class only_render_codeblocks(ColumnData, Boolean, GuildSetting):
    attr_name = "only_render_codeblocks"
    category = "LaTeX"
    read_check = None
    write_check = guild_manager

    name = "only_render_codeblocks"
    desc = "Only render LaTeX found in codeblocks."

    long_desc = ("Whether automatic LaTeX recognition will only read and render codeblocks.")

    _outputs = {True: "True",
                False: "False"}

    _default = LatexGuild.defaults['require_codeblocks']

    _table_interface_name = "guild_latex_config"
    _data_column = "require_codeblocks"
    _delete_on_none = False

    def write(self, **kwargs):
        """
        Write data and update stored LatexGuild
        """
        super().write(**kwargs)
        LatexGuild.get(self.guildid).load()


@module.guild_setting
class latex_level(ColumnData, IntegerEnum, GuildSetting):
    attr_name = "latex_level"
    category = "LaTeX"
    read_check = None
    write_check = guild_manager

    name = "latex_level"
    desc = "How strict the parser is when looking for LaTeX in messages."
    accepts = "One of `WEAK`, `STRICT` or `CODEBLOCK`."

    long_desc = "Sets how strict the parser is when detecting LaTeX."

    _default = LatexGuild.defaults['autotex_level']
    _enum = AutoTexLevel

    _table_interface_name = "guild_latex_config"
    _data_column = "autotex_level"
    _delete_on_none = False

    @property
    def embed(self, *args, **kwargs):
        embed = super().embed
        embed.add_field(
            name="Options",
            value=(
                "`CODEBLOCK`: The strictest level, require a `tex` or `latex` syntax codeblock.\n"
                "`STRICT`: Also recognise environments, double dollars, `\(...\)` and `\[...\]`.\n"
                "`WEAK`: Also recognise paired single dollars."
            )
        )
        return embed

    def write(self, **kwargs):
        """
        Write data and update stored LatexGuild
        """
        super().write(**kwargs)
        LatexGuild.get(self.guildid).load()


@module.guild_setting
class latex_channels(ListData, ChannelList, GuildSetting):
    attr_name = "latex_channels"
    category = "LaTeX"

    name = "latex_channels"
    desc = "Restrict automatic detection of LaTeX to these channels."

    long_desc = "If set, I will only detect LaTeX from messages in these channels."

    _table_interface_name = "guild_latex_channels"
    _data_column = "channelid"

    def write(self, **kwargs):
        """
        Write data and update stored LatexGuild
        """
        super().write(**kwargs)
        LatexGuild.get(self.guildid).load()

    @classmethod
    def _format_data(cls, *args, **kwargs):
        """
        Add a default to the data formatter.
        """
        formatted = super()._format_data(*args, **kwargs)
        if formatted is None:
            return "All Channels"

        return formatted
