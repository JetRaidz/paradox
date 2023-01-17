from datetime import datetime

import discord

from utils.lib import prop_tabulate

from .module import latex_module as module

from .core.LatexUser import LatexUser
from .core.LatexGuild import LatexGuild

from constants import ParaCC


@module.cmd("texconfig",
            desc="View or modify your personal LaTeX rendering options.",
            aliases=['texflags', 'tc'])
async def cmd_texconfig(ctx):
    """
    Usage``:
        {prefix}texconfig
        {prefix}texconfig help
        {prefix}texconfig <setting>
        {prefix}texconfig <setting> <value>
    Description:
        Configuration interface to view and modify the various
        options affecting your LaTeX compilation.
        These are *personal* configuration options,
        use the `config` command to view the *guild* configuration.

        When used with no arguments, displays your current configuration.

        When used with `help`, displays brief descriptions of each option.

        When used with a `setting`, displays detailed information
        about that setting, or sets the setting to the provided `value`.
    Related:
        autotex, preamble, tex
    Setting Examples``:
        {prefix}texconfig colour dark
        {prefix}texconfig keepsourcefor 30
        {prefix}texconfig colour dark
        {prefix}texconfig alwaysmath on
        {prefix}texconfig alwayswide on
        {prefix}texconfig namestyle NICKNAME
        {prefix}texconfig autotex_level STRICT
    """
    # Build the latex user
    luser = LatexUser.get(ctx.author.id)

    if not ctx.args or ctx.args.lower() == "help":
        # Display the configuration options with either values or the descriptions

        # Determine whether we want to show values or descriptions
        show_desc = bool(ctx.args)

        # Build the appropriate table
        properties = list(luser.settings.keys())
        if show_desc:
            values = [luser.settings[name].desc for name in properties]
        else:
            values = [
                luser.settings[name]._format_data(
                    ctx.client,
                    ctx.author.id,
                    luser.settings[name]._data_from_value(
                        ctx.client,
                        ctx.author.id,
                        getattr(luser, name)
                    )
                ) for name in properties
            ]
        setting_table = prop_tabulate(properties, values)

        # Create the description
        desc = (
            "{0}\n"
            "To see more detailed information use `{1}texconfig <option>`.\n"
            "To set an option use `{1}texconfig <option> <value>`."
        ).format(setting_table, ctx.best_prefix())

        # Create the preamble field contents
        if show_desc:
            preamble_field = (
                "Personal persistent compilation preamble, "
                "used for defining macros and importing packages "
                "that may be used across all compilations.\n"
                "See `{}help preamble` for more information."
            ).format(ctx.best_prefix())
        else:
            if luser.preamble:
                preamble_field = (
                    "Using a custom personal preamble with `{}` lines!"
                ).format(len(luser.preamble.splitlines()))
            else:
                lguild = LatexGuild.get(ctx.guild.id if ctx.guild else 0)
                if lguild.preamble:
                    preamble_field = (
                        "No personal preamble, using the custom guild preamble with `{}` lines."
                    ).format(len(lguild.preamble.splitlines()))
                else:
                    preamble_field = (
                        "No personal or guild preamble, using the global default preamble."
                    )

            preamble_field += "\nUse `{}preamble` to view or modify your preamble!".format(ctx.best_prefix())

        # We have all the components, build the embed and post
        embed = discord.Embed(
            title="Personal LaTeX configuration.",
            description=desc,
            timestamp=datetime.utcnow(),
            color=ParaCC["purple"]
        )
        embed.add_field(name="Preamble", value=preamble_field)

        await ctx.reply(embed=embed)
    else:
        # View or set a given option

        # First obtain the option
        splits = ctx.args.split(maxsplit=1)
        option = splits[0].lower()
        valuestr = splits[1] if len(splits) > 1 else None

        # Handle aliases
        if option == "color":
            option = "colour"

        # Retrieve the corresponding setting, if possible
        if option == "preamble":
            return await ctx.error_reply("Use the `preamble` command to view or modify your preamble.")
        elif option not in luser.settings:
            return await ctx.error_reply(
                "I don't recognise the option `{}`. "
                "Use `{}texconfig` to see the list of options.".format(
                    option,
                    ctx.best_prefix()
                )
            )
        else:
            setting = luser.settings[option]
            current_value = getattr(luser, option)

        if not valuestr:
            # View information about the option
            await ctx.reply(embed=setting.info_embed(ctx, current_value))
        else:
            # Set the option
            await setting.user_set(ctx, valuestr.lower())


@module.cmd("autotex",
            desc="Toggle whether your LaTeX is automatically rendered.",
            aliases=['texlisten'])
async def cmd_autotex(ctx):
    """
    Usage``:
        {prefix}autotex [on | off]
        {prefix}autotex <level>
    Description:
        When used with no arguments, toggles your personal `autotex` setting,
        that controls whether your LaTeX is automatically rendered.

        When given `level`, enables `autotex` and sets your LaTeX recognition level.

        See `{prefix}texconfig autotex` and `{prefix}texconfig autotex_level`
        for more information about these settings.
    About automatic compilation:
        LaTeX will be automatically compiled when *all* of the following are true.
        • Either your `autotex` or the guild's `latex` setting are enabled.
        • The message is in a guild `latex_channel`, if set.
        • The message matches the *most strict* of your `autotex_level` and the guild's `latex_level`.
    Examples``:
        {prefix}autotex
        {prefix}autotex WEAK
        {prefix}autotex STRICT
        {prefix}autotex CODEBLOCK
    """
    # Build the latex user
    luser = LatexUser.get(ctx.author.id)

    largs = ctx.args.lower()
    if not largs or largs in ['on', 'off']:
        # No arguments, toggle the user's listening setting.
        if largs == 'off' or (not largs and luser.autotex):
            luser.settings["autotex"].save(ctx.client, ctx.author.id, False)
            await ctx.reply(
                "You have *disabled* personal automatic LaTeX compilation.\n"
                "Please be aware that LaTeX will still be rendered in guilds "
                "with the `latex` setting enabled.\n"
                "See `{}help autotex` for more information about automatic compilation.".format(ctx.best_prefix())
            )
        elif largs == 'on' or not (largs or luser.autotex):
            luser.settings["autotex"].save(ctx.client, ctx.author.id, True)
            await ctx.reply(
                "You have *enabled* personal automatic LaTeX compilation, "
                "with LaTeX recognition level `{}`.\n"
                "Please be aware that automatic compilation may be restricted by guild settings.\n"
                "See `{}help autotex` for more information about automatic compilation.".format(
                    luser.autotex_level.name,
                    ctx.best_prefix()
                )
            )
    elif largs in ['codeblock', 'strict', 'weak']:
        if not luser.autotex:
            luser.settings["autotex"].save(ctx.client, ctx.author.id, True)
        luser.settings["autotex_level"].save(
            ctx.client,
            ctx.author.id,
            await luser.settings["autotex_level"]._parse_userstr(ctx, ctx.author.id, largs)
        )

        await ctx.reply(
            "You have enabled personal automatic LaTeX compilation with recognition level `{}`.".format(largs.upper())
        )
    else:
        await ctx.error_reply(
            "Unrecognised compilation level `{}`.\n"
            "See `{}texconfig autotex_level` for the valid options.".format(largs, ctx.best_prefix())
        )
