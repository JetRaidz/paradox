import discord

from settings import SettingType, Boolean, Integer, String, IntegerEnum, BadUserInput
from utils.lib import prop_tabulate

from .tex_utils import TexNameStyle, AutoTexLevel
from . import user_data  # noqa

from constants import ParaCC


class LatexUserSetting(SettingType):
    """
    Abstract base class for a `LatexUser` setting.
    Intended to hold the logic for conversion between the following setting representations,
    and additionally storing the data.

    data:
        The setting data as stored in the database.
    value:
        The setting value, as used in the application.
    userstr:
        The user-input which possibly represents setting information.
    formatted_data:
        The setting information in a human readable form, accounting for context.

    Uses the `SettingType` abstract mixin interface.
    """
    # The human-readable name of the setting
    name: str = None

    # The default setting value
    default = None

    # The message to send on parsing failure (i.e. BadUserInput)
    _parsing_failed_response: str = None

    # The data column name
    _data_column: str = None

    # The upsert constraint
    _upsert_constraint = "userid"

    @classmethod
    def save(cls, client, userid, data):
        """
        Uses the appropriate tableInterface to save the data.
        """
        params = {
            "userid": userid,
            cls._data_column: data
        }

        client.data.user_latex_config.upsert(
            constraint=cls._upsert_constraint,
            **params
        )

    @classmethod
    def response(cls, ctx, new_data):
        """
        Generate the appropriate response, possibly dynamically, after successfuly setting the property.
        """
        raise NotImplementedError

    @classmethod
    def info_embed(cls, ctx, current_data):
        """
        A detailed embed for the setting.
        Must be provided the current data value.
        """
        embed = discord.Embed(
            title="Configuration options for `{}`".format(cls.name),
            color=ParaCC["purple"]
        )
        fields = ("Current value", "Default value", "Accepted input")
        values = (cls._format_data(ctx.client, ctx.author.id, current_data),
                  cls._format_data(ctx.client, ctx.author.id, cls.default) or "None",
                  cls.accepts)
        table = prop_tabulate(fields, values)
        embed.description = "{}\n{}".format(cls.desc, table)
        return embed

    @classmethod
    async def user_set(cls, ctx, userstr):
        """
        Set a user setting given a message context, handling parsing, saving, and responses.
        """
        user = ctx.author
        try:
            data = await cls._parse_userstr(ctx, user.id, userstr)
        except BadUserInput as e:
            response = (cls._parsing_failed_response or
                        "{error.msg}\n")

            desc = response.format(
                ctx=ctx,
                userstr=userstr,
                prefix=ctx.best_prefix(),
                cls=cls,
                error=e
            )

            embed = discord.Embed(title="Couldn't parse your input!",
                                  description=desc,
                                  color=discord.Color.red())
            embed.set_footer(
                text="Use {}texconfig {} to see more detailed information about this setting.".format(
                    ctx.best_prefix(),
                    cls.name
                )
            )

            return await ctx.reply(embed=embed)

        cls.save(ctx.client, user.id, data)
        response = cls.response(ctx, data)
        return await ctx.reply(response)


class autotex(LatexUserSetting, Boolean):
    name = "autotex"
    desc = "Whether to automatically compile LaTeX in your messages."

    default = False
    _outputs = {
        True: "Enabled (may be restricted by guild settings)",
        False: "Disabled (may be overriden by guild settings)"
    }
    _parsing_failed_response = "Unknown option `{userstr}`.\nPlease use `on` or `off`."

    _data_column = "autotex"

    @classmethod
    def response(cls, ctx, data):
        if data is None:
            return ("Unset `autotex`!")
        elif data is True:
            return ("I will now listen for and compile LaTeX in your messages! "
                    "Be aware that automatic compilation may be "
                    "restricted by other guild and personal settings.")
        elif data is False:
            return ("You have disabled personal automatic compilation! "
                    "Messages will still be automatically compiled "
                    "in guilds with the `latex` setting enabled.")


class keepsourcefor(LatexUserSetting, Integer):
    name = "keepsourcefor"
    desc = "How many seconds to keep source for after compilation ('None' to never delete)."
    accepts = "A non-negative number of seconds, or `None` to keep forever."

    default = None
    _min = 0
    _parsing_failed_response = "{error.msg}"

    _data_column = "keepsourcefor"

    @classmethod
    def _format_data(cls, client, userid, data, **kwargs):
        """
        Add some decoration to the number, and handle the default.
        """
        if data is None:
            return "Don't delete source (may be overriden by the guild)"
        else:
            return "`{}` seconds".format(data)

    @classmethod
    def response(cls, ctx, data):
        if data is None:
            return "No longer automatically deleting your LaTeX source."
        else:
            return ("Your source will be deleted {} seconds "
                    "after a succesful compilation (if not edited).").format(data)


class colour(LatexUserSetting, String):
    desc = "Your LaTeX colourscheme."
    name = "colour"
    accepts = "One of the colourschemes listed below."

    colourschemes = {
        "white": "Pure white background, with black text.",
        "light": "Very light grey bckground, with black text.",
        "grey": "Discord-grey background, with white text. (Recommended)",
        "darkgrey": "Dark grey background, with white text.",
        "dark": "Dark background, with white text.",
        "black": "Pure black background, with white text.",
        "transparent": "Transparent background, with white text. (May cause issues)",
        "trans_black": "Transparent background, with black text. (May cause issues)"
    }
    tabled_colourschemes = prop_tabulate(list(colourschemes.keys()), list(colourschemes.values()))

    default = "grey"
    _options = list(colourschemes.keys()) + ["gray", "trans_white"]
    _parsing_failed_response = ("Unknown colourscheme `{{userstr}}`. "
                                "Valid colourschemes:\n{}".format(tabled_colourschemes))

    _data_column = "colour"

    @classmethod
    def _format_data(cls, client, userid, data, **kwargs):
        """
        Add some decoration to the number, and handle the default.
        """
        if data is None:
            return "Using the default colourscheme"
        else:
            return "Using the `{}` colourscheme".format(data)

    @classmethod
    def info_embed(cls, ctx, data):
        embed = super().info_embed(ctx, data)
        embed.add_field(name="Colourschemes", value=cls.tabled_colourschemes)
        return embed

    @classmethod
    def response(cls, ctx, data):
        if data is None:
            return "You are now using the default colourscheme."
        else:
            return "You have switched to the `{}` colourscheme.".format(data)


class alwaysmath(LatexUserSetting, Boolean):
    name = "alwaysmath"
    desc = "Whether to always use mathmode with the `tex` command."

    default = False
    _outputs = {
        True: "Enabled",
        False: "Disabled"
    }
    _parsing_failed_response = "Unknown option `{userstr}`.\nPlease use `on` or `off`."

    _data_column = "alwaysmath"

    @classmethod
    def response(cls, ctx, data):
        if not data:
            return "The `tex` command will now render in paragraph mode, as usual."
        else:
            return "The `tex` command will now render in maths mode, i.e., in a `gather*` environment."


class alwayswide(LatexUserSetting, Boolean):
    name = "alwayswide"
    desc = "Whether to skip the automatic horizontal addition of transparent pixels to LaTeX output."

    default = False
    _outputs = {
        True: "Enabled",
        False: "Disabled"
    }
    _parsing_failed_response = "Unknown option `{userstr}`.\nPlease use `on` or `off`."

    _data_column = "alwayswide"

    @classmethod
    def response(cls, ctx, data):
        if not data:
            return ("Transparent pixels will be added to your rendered LaTeX to improve previews.\n"
                    "Use the `texw` command to disable this for a single compile.")
        else:
            return ("Transparent pixels will no longer be added to your rendered LaTeX.\n"
                    ":warning: If your input is short, Discord will make the rendered image huge!")


class namestyle(LatexUserSetting, IntegerEnum):
    name = "namestyle"
    desc = "The type of name to display with your LaTeX output."
    accepts = "One of the types listed below."
    namestyles = {
        "USERNAME": "Your global username. (**{ctx.author.name}**)",
        "NICKNAME": "Your server nickname. (**{ctx.author.display_name}**)",
        "MENTION": "A mention. {ctx.author.mention}",
        "HIDDEN": "No name."
    }

    default = TexNameStyle.NICKNAME.value
    _enum = TexNameStyle
    _parsing_failed_response = "Unknown namestyle `{{userstr}}`. Valid namestyles:\n{}".format(
                                    prop_tabulate(list(namestyles.keys()), list(namestyles.values()))
                                )

    _data_column = "namestyle"

    @classmethod
    def response(cls, ctx, data):
        if data is None:
            return "Your namestyle has been returned to the default."
        elif data == TexNameStyle.USERNAME.value:
            return "Your username will now be shown on your LaTeX output."
        elif data == TexNameStyle.NICKNAME.value:
            return "Your guild nickname, if set, will now be shown on your LaTeX output."
        elif data == TexNameStyle.MENTION.value:
            return "You will now be mentioned with your LaTeX output."
        elif data == TexNameStyle.HIDDEN.value:
            return ("Your name will no longer be shown on LaTeX output.\n"
                    "Note that the name of the output image is your userid, so you are still identifiable.")

    @classmethod
    def info_embed(cls, ctx, data):
        embed = super().info_embed(ctx, data)
        props = cls.namestyles.keys()
        values = [val.format(ctx=ctx) for val in cls.namestyles.values()]
        embed.add_field(name="Name styles", value=prop_tabulate(props, values))
        return embed


class autotex_level(LatexUserSetting, IntegerEnum):
    name = "autotex_level"
    desc = "How strict the parser is when looking for LaTeX in your messages."
    accepts = "One of the levels listed below."

    tex_levels = {
        "CODEBLOCK": r"The strictest level, require a `tex` or `latex` syntax codeblock.",
        "STRICT": r"Also recognise environments, `$$...$$`, `\(...\)` and `\[...\]`.",
        "WEAK": r"Also recognise paired single dollars, i.e. `$...$`.",
    }
    tabled_levels = prop_tabulate(list(tex_levels.keys()), list(tex_levels.values()))

    default = AutoTexLevel.WEAK
    _enum = AutoTexLevel
    _parsing_failed_response = ("Unknown autotex level `{{userstr}}`. "
                                "Valid levels:\n{}".format(tabled_levels))

    _data_column = "autotex_level"

    @classmethod
    def response(cls, ctx, data):
        if data is None:
            return "Reset your autotex level to default."
        elif data == AutoTexLevel.CODEBLOCK:
            return "I will now only render your messages with `tex` or `latex` codeblocks."
        elif data == AutoTexLevel.STRICT:
            return ("I will now require explicit mathmode macros, environments or codeblocks to render your messages.\n"
                    "Guild configuration (`latex_level`) may locally upgrade this to `CODEBLOCK`.")
        elif data == AutoTexLevel.WEAK:
            return ("I will now do my best to detect all LaTeX in your messages.\n"
                    "Guild configuration (`latex_level`) may locally upgrade this to `STRICT` or `CODEBLOCK`.")

    @classmethod
    def info_embed(cls, ctx, data):
        embed = super().info_embed(ctx, data)
        embed.add_field(name="LaTeX Levels", value=cls.tabled_levels)
        return embed
