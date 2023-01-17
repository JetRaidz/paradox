from .module import meta_module as module

from . import userprefix_data  # noqa

"""
Provides a prefix command.

Commands provided:
    prefix:
        View current valid bot prefixes and set a personal prefix.

Initialisation:
    load_user_prefixes:
        Read user prefixes from data and load them into the cache.
    ensure_prefix_properties:
        Ensure that the required user and guild properties exist.

Client objects:
    user_prefix_cache:  Dict[int, str]
        Dictionary `{userid: prefix}` of custom user prefixes.

User properties:
    custom_prefix: str
        (app agnostic, user configured)
        Current user custom prefix.
        Must be less than `5` characters.
"""


@module.cmd("prefix",
            desc="View bot prefixes and set a personal prefix.",
            aliases=["myprefix"],
            flags=["set", "reset"])
async def cmd_prefix(ctx, flags):
    """
    Usage``:
        {prefix}prefix
        {prefix}prefix [--set] [custom prefix]
        {prefix}prefix --reset
    Description:
        Displays the current command prefixes available for the bot,
        including the global, guild, and personal prefix where applicable.

        Use `{prefix}config prefix <prefix>` to change the guild prefix.
        *Note that mentioning the bot will always work as a prefix.*
    Flags::
        set: Set your personal prefix (this will work additionally to the current prefixes).
        reset: Remove your presonal prefix.
    Related:
        config
    Examples``:
        {prefix}prefix
        {prefix}prefix --set !!
    """
    # Get the user's prefix and update the cache
    rows = ctx.client.data.user_prefixes.select_where(userid=ctx.author.id)
    prefix = rows[0]['prefix'] if rows else None
    if prefix:
        ctx.client.objects["user_prefix_cache"][ctx.author.id] = prefix
    else:
        ctx.client.objects["user_prefix_cache"].pop(ctx.author.id, None)

    # Handle the flags and arguments
    if flags["reset"]:
        # Removes the previously-stored prefix
        ctx.client.objects["user_prefix_cache"].pop(ctx.author.id, None)
        ctx.client.data.user_prefixes.delete_where(userid=ctx.author.id)

        # Inform the user
        await ctx.reply("Your personal command prefix has successfully been removed!\n"
                        "Mentions and the current guild or global prefix will still function.")

    elif flags["set"] or ctx.args:
        prefix = ctx.args

        # First check if the provided prefix is of an adequate length
        if len(prefix) > 5:
            return await ctx.error_reply("Sorry, the maximum length of a personal prefix is `5` characters.")
        if len(prefix) == 0:
            return await ctx.error_reply("No prefix was provided! Please try again.")

        # Set the prefix user property
        ctx.client.data.user_prefixes.insert(
            allow_replace=True,
            userid=ctx.author.id,
            prefix=prefix
        )

        # Update the user prefix cache
        ctx.client.objects["user_prefix_cache"][ctx.author.id] = prefix

        # Inform the user
        await ctx.reply("Your personal command prefix has been set to `{}`.\n"
                        "Mentions and the current guild or global prefix will still function.".format(prefix))

    else:
        # Retrieve the current bot prefixes and build the response lines
        # User's personal prefix
        personal_prefix = prefix
        if personal_prefix:
            personal_str = "Your personal prefix is `{}`.".format(personal_prefix)
        else:
            personal_str = "You have not set a personal prefix."

        # Guild prefix, if applicable
        guild_str = ""
        guild_prefix = None
        if ctx.guild:
            guild_prefix = ctx.client.objects["guild_prefix_cache"].get(ctx.guild.id, None)
            guild_str = ("The guild prefix is `{}`.".format(guild_prefix)
                         if guild_prefix else "No custom guild prefix set.")

        # Global prefix
        global_str = "The default prefix is `{}`{}.".format(
            ctx.client.prefix,
            " (not active in favour of the guild prefix)" if guild_prefix else ""
        )

        # Create the response and reply
        await ctx.reply(
            "{}\n{}\n{}\nMentioning me will always work as a prefix: {}".format(
                personal_str, guild_str, global_str, ctx.client.user.mention
            )
        )
