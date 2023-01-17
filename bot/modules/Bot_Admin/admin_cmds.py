import discord
import aiohttp
import inspect

from cmdClient import Context
from .module import bot_admin_module as module
from wards import is_master, is_manager

from utils.ctx_addons import format_usage  # noqa
from utils.interactive import pager  # noqa
from utils.lib import split_text


"""
Administration level commands for the bot
All commands require manager or master level permissions.

Commands provided:
    shutdown:
        Shuts down the bot, that's all
    setinfo:
        Sets the bot status, game/avatar/playing message
    dm:
        Sends a dm to the user with user id given
    logs:
        Attempts to send the logfile or last n lines of the log.
    showcmd:
        View the source of the specified command.
"""

status_dict = {"online": discord.Status.online,
               "offline": discord.Status.offline,
               "idle": discord.Status.idle,
               "dnd": discord.Status.dnd,
               "invisible": discord.Status.invisible}


activity_dict = {
    "playing": discord.ActivityType.playing,
    "streaming": discord.ActivityType.streaming,
    "listening": discord.ActivityType.listening,
    "watching": discord.ActivityType.watching
}


@module.cmd("shutdown",
            desc="Shut down the client.",
            aliases=["restart"])
@is_manager()
async def cmd_shutdown(ctx: Context):
    """
    Usage``:
        {prefix}shutdown
    Description:
        Closes the client and shuts down the bot.

        *Requires you to be an owner of the bot.*
    """
    await ctx.reply("Shutting down...")
    await ctx.client.close()


@module.cmd("setinfo",
            desc="Set my game, avatar, and status",
            aliases=["status", "setgame", "setstatus"],
            flags=["type=", "desc==", "url==", "avatar==", "status="])
@is_manager()
async def cmd_setgame(ctx: Context, flags):
    """
    Usage``:
        {prefix}setinfo [--type activity type] [--desc activity] [--url url] [--status status] [--avatar avatar_url]
    Description:
        Sets the current bot status and activity.

        *Requires you to be an owner of the bot.*
    Flags::
        type: Type of activity (see Activity Types section below).
        desc: Name of activity to show (shown after `playing`, `listening` etc).
        url: Streaming url if applicable.
        status: Client status (see Status section below).
        avatar: URL of the new avatar. Make sure you have a copy of the old one!
    Activity Types:
        One of `playing`, `streaming`, `listening` or `watching`.
    Status:
        One of `online`, `offline`, `idle` or `dnd`.
    """
    # Set the avatar if required
    if flags["avatar"]:
        avatar_url = flags["avatar"]
        async with aiohttp.get(avatar_url) as r:
            response = await r.read()
        await ctx.client.user.edit(avatar=response)

    # Build the activity
    activity = None
    if flags["desc"] or flags["type"]:
        activity = discord.Activity(
            type=activity_dict[flags["type"]] if flags["type"] else discord.ActivityType.playing,
            name=flags["desc"] or None,
            url=flags["url"] or None
        )

    # Change the presence
    if flags["status"] or activity:
        await ctx.client.change_presence(status=flags["status"] or None, activity=activity)

    # Inform the user
    await ctx.reply("Updated!")


@module.cmd("dm",
            desc="Sends a direct message to a user, if possible.")
@is_master()
async def cmd_dm(ctx: Context):
    """
    Usage``:
        {prefix}dm user_id message
    Description:
        Sends the specified message to the given `user_id` if possible.
    """
    # Parse the arguments
    splits = ctx.args.split(maxsplit=1)
    if len(splits) < 2 or not splits[0].isdigit():
        return await ctx.error_reply(ctx.format_usage())

    userid, message = splits
    userid = int(userid)

    # Find the user
    user = ctx.client.get_user(userid)
    if user is None:
        try:
            user = await ctx.client.fetch_user(userid)
        except discord.NotFound:
            return await ctx.error_reply("This user does not exist!")

    # We can't send messages to ourself
    if user == ctx.client.user:
        return await ctx.error_reply("I cannot send a message to myself!")

    # Send the message
    try:
        await user.send(message)
    except discord.Forbidden:
        await ctx.error_reply(
            "I couldn't send the message. Maybe we don't share any servers with this user or they have us blocked?"
        )
    else:
        await ctx.reply("Message sent!")


@module.cmd("logs",
            desc="Read and return the bot logs.")
@is_master()
async def cmd_logs(ctx: Context):
    """
    Usage``:
        {prefix}logs [lines]
    Description:
        Sends the logfile or the last `<lines>` lines of the log.
    """
    # Get the path to the log file from config
    logpath = ctx.client.conf.get('LOGFILE')

    if not ctx.args:
        # Attempt to send the logfile
        logfile = discord.File(logpath)
        try:
            await ctx.reply(file=logfile)
        except discord.HTTPException:
            await ctx.error_reply("Could not send the logfile. Perhaps it was too large?")
    else:
        # Retrieve the number of lines to send
        if not ctx.args.isdigit():
            return await ctx.error_reply(ctx.format_usage())
        lines = int(ctx.args)

        # Run tail to get the last <lines> lines of the log
        logs = await ctx.run_in_shell("tail -n {} {}".format(lines, logpath))

        # Split the log blocks and page the result
        await ctx.pager(split_text(logs))


@module.cmd("showcmd",
            desc="Shows the source of a command.")
@is_master()
async def cmd_showcmd(ctx: Context):
    """
        Usage:
            {prefix}showcmd <name>
        Description:
            Replies with the source for the specified command.
    """
    if not ctx.arg_str:
        return await ctx.error_reply("Please provide a command name.")

    # Get the command from the user arguments
    command = ctx.client.cmd_names.get(ctx.arg_str, None)
    if not command:
        return await ctx.error_reply("No command found.")

    cmd_func = command.func
    source = inspect.getsource(cmd_func)
    source = source.replace('```', '[codeblock]')
    blocks = split_text(source, 1800, syntax='python')

    await ctx.offer_delete(await ctx.pager(blocks, locked=False))
