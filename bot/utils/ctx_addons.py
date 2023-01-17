import asyncio
import logging

import discord
from cmdClient import Context
from cmdClient.lib import SafeCancellation

import logger
from . import lib


@Context.util
async def embedreply(ctx, desc, colour=discord.Colour(0x9b59b6), **kwargs):
    """
    Simple helper to embed replies.
    All arguments are passed to the embed constructor.
    `desc` is passed as the `description` kwarg.
    """
    embed = discord.Embed(description=desc, colour=colour, **kwargs)
    return await ctx.reply(embed=embed)


@Context.util
async def live_reply(ctx, reply_func, update_interval=5, max_messages=20):
    """
    Acts as `ctx.reply`, but asynchronously updates the reply every `update_interval` seconds
    with the value of `reply_func`, until the value is `None`.

    Parameters
    ----------
    reply_func: coroutine
        An async coroutine with no arguments.
        Expected to return a dictionary of arguments suitable for `ctx.reply()` and `Message.edit()`.
    update_interval: int
        An integer number of seconds.
    max_messages: int
        Maximum number of messages in channel to keep the reply live for.

    Returns
    -------
    The output message after the first reply.
    """
    # Send the initial message
    message = await ctx.reply(**(await reply_func()))

    # Start the counter
    future = asyncio.ensure_future(_message_counter(ctx.client, ctx.ch, max_messages))

    # Build the loop function
    async def _reply_loop():
        while not future.done():
            await asyncio.sleep(update_interval)
            args = await reply_func()
            if args is not None:
                await message.edit(**args)
            else:
                break

    # Start the loop
    asyncio.ensure_future(_reply_loop())

    # Return the original message
    return message


async def _message_counter(client, channel, max_count):
    """
    Helper for live_reply
    """
    # Build check function
    def _check(message):
        return message.channel == channel

    # Loop until the message counter reaches maximum
    count = 0
    while count < max_count:
        await client.wait_for('message', check=_check)
        count += 1
    return


@Context.util
def log(ctx: Context, *args, **kwargs):
    """
    Shortcut to the logger which automatically adds the context.
    """
    if "context" not in kwargs:
        kwargs['context'] = "mid:{}".format(ctx.msg.id)
    logger.log(*args, **kwargs)


@Context.util
async def run_in_shell(ctx: Context, script):
    """
    Execute a script or command asynchronously in a subprocess shell.
    """
    process = await asyncio.create_subprocess_shell(script, stdout=asyncio.subprocess.PIPE)
    ctx.log(
        "Executing the following script:\n{}\nwith pid '{}'.".format(
            "\n".join("\t{}".format(line) for line in script.splitlines()),
            process.pid
        ),
        level=logging.DEBUG
    )
    stdout, stderr = await process.communicate()
    ctx.log("Completed the script with pid '{}'{}".format(
        process.pid,
        " with errors" if process.returncode != 0 else ""),
        level=logging.DEBUG
    )
    return stdout.decode(errors='backslashreplace').strip()


@Context.util
def best_prefix(ctx: Context):
    """
    Returns the best default prefix in the current context.
    This will be the server prefix if it is defined,
    otherwise the default client prefix.
    """
    if ctx.guild:
        prefix = ctx.client.objects["guild_prefix_cache"].get(ctx.guild.id, ctx.client.prefix)
    else:
        prefix = ctx.client.prefix
    return prefix


@Context.util
def format_usage(ctx: Context):
    """
    Formats the usage string of the current command.
    Assumes the first section of the doc string is the usage string.
    """
    usage = ctx.cmd.long_help[0][1]
    usage = usage.format(ctx=ctx, client=ctx.client, prefix=ctx.best_prefix())
    return "**USAGE:**{}{}".format(
        '\n' if '\n' in usage else ' ',
        usage
    )


@Context.util
async def confirm_sent(ctx: Context, msg=None, reply=None):
    """
    Confirms to a user that the bot has DMed them by adding a tick reaction to the command message.
    If the bot doesn't have permission to add reactions, it will respond with a message if reply is provided.
    Parameters
    ----------
    msg: Message
        The message to add the reaction to, otherwise assumes ctx.msg.
    reply: str
        A custom response to confirm the message has been sent, if the bot lacks permission to add reactions.
    """
    try:
        if not msg:
            await ctx.msg.add_reaction("✅")
        else:
            await msg.add_reaction("✅")
    except discord.Forbidden:
        return await ctx.reply(reply if reply else "Check your DMs!")


@Context.util
async def offer_delete(ctx: Context, *to_delete, timeout=300):
    """
    Offers to delete the provided messages via a reaction on the last message.
    Removes the reaction if the offer times out.

    If any exceptions occur, handles them silently and returns.

    Parameters
    ----------
    to_delete: List[Message]
        The messages to delete.

    timeout: int
        Time in seconds after which to remove the delete offer reaction.
    """
    # Get the delete emoji from the config
    emoji = ctx.client.conf.emojis.getemoji("delete")

    # Return if there are no messages to delete
    if not to_delete:
        return

    # The message to add the reaction to
    react_msg = to_delete[-1]

    # Build the reaction check function
    if ctx.guild:
        modrole = ctx.get_guild_setting.modrole.value if ctx.guild else None

        def check(reaction, user):
            if not (reaction.message.id == react_msg.id and reaction.emoji == emoji):
                return False
            if user == ctx.guild.me:
                return False
            return ((user == ctx.author)
                    or (ctx.ch.permissions_for(user).manage_messages)
                    or (modrole and modrole in user.roles))
    else:
        def check(reaction, user):
            return user == ctx.author and reaction.message.id == react_msg.id and reaction.emoji == emoji

    try:
        # Add the reaction to the message
        await react_msg.add_reaction(emoji)

        # Wait for the user to press the reaction
        reaction, user = await ctx.client.wait_for("reaction_add", check=check, timeout=timeout)

        # Since the check was satisfied, the reaction is correct. Delete the messages, ignoring any exceptions
        deleted = False
        # First try to bulk delete if we have the permissions
        if ctx.guild and ctx.ch.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.ch.delete_messages(to_delete)
                deleted = True
            except Exception:
                deleted = False

        # If we couldn't bulk delete, delete them one by one
        if not deleted:
            try:
                asyncio.gather(*[message.delete() for message in to_delete], return_exceptions=True)
            except Exception:
                pass
    except (asyncio.TimeoutError, asyncio.CancelledError):
        # Timed out waiting for the reaction, attempt to remove the delete reaction
        try:
            await react_msg.remove_reaction(emoji, ctx.client.user)
        except Exception:
            pass
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass
    except discord.HTTPException:
        pass


@Context.util
async def mail(ctx, channelid, content=None, **kwargs):
    """
    Mails a message to a channel not necessarially seen by the gateway.
    (e.g. on another shard.)
    All arguments apart from `channelid` are passed transparently to `lib.mail`
    and then onto a minimal `Messageable` instance created from `channelid`.
    """
    return await lib.mail(ctx.client, channelid, content=content, **kwargs)


@Context.util
async def safe_delete_msgs(ctx: Context, *msgs):
    """
    Safely deletes a list of messages, ignoring any exceptions that could be raised.

    Parameters
    ----------
    msgs: Message
        The message(s) to delete.
    """
    try:
        await asyncio.gather(*[msg.delete() for msg in msgs], return_exceptions=True)
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass
    except Exception:
        pass


@Context.util
async def dm_reply(ctx: Context, *args, **kwargs):
    """
    Respond to a user by DMing them.

    Raises
    ----------
    discord.Forbidden:
        We're not allowed to DM the user.
    """
    try:
        await ctx.author.send(*args, **kwargs)
    except discord.Forbidden:
        raise SafeCancellation("I can't DM you! Do you have DMs disabled?")


@Context.util
def clean_arg_str(ctx: Context):
    """
    Re-parse a command message using `Message.clean_content`
    to clean mentions from the arguments.

    Returns: str
        The clean version of `Context.arg_str`.
    """
    # TODO: Apply the content cleaner manually to `ctx.args` and/or `ctx.arg_str`.
    content = ctx.msg.clean_content

    if ctx.prefix == ctx.alias:
        content = content[len(ctx.prefix):]

    return content.partition(ctx.alias)[2].strip()


@Context.util
def usage_embed(ctx: Context, custom_usage=None):
    """
    Creates an embed displaying the current command's usage field.
    If `custom_usage` is provided, uses this instead of the help usage field.

    Returns: discord.Embed
        The usage embed for the current command.
    """
    if not ctx.cmd:
        raise ValueError("Cannot extract usage from a non-command context.")
    if not custom_usage:
        fields = ctx.cmd.long_help
        usage_field = next((pair for pair in fields if pair[0].startswith('Usage')), None)
        if usage_field is None:
            raise ValueError("Cannot extract usage from command with no usage field.")
        if usage_field[0].endswith('``'):
            value = "`{}`".format('`\n'.join(usage_field[1].splitlines()))
    else:
        value = custom_usage
    return discord.Embed(title="Usage", colour=discord.Color.red(), description=value)
