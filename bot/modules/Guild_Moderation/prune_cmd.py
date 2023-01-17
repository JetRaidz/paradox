import discord
import asyncio
# from datetime import datetime

from cmdClient.lib import ResponseTimedOut, UserCancelled

from wards import guild_moderator, chunk_guild
from utils import seekers  # noqa

from .module import guild_moderation_module as module


@module.cmd("prune",
            desc="Purges messages matching selected criteria from the current channel.",
            aliases=["purge"],
            flags=["r==", "bot", "bots", "user", "embed", "file", "me", "from==", "after==", "force"])
@guild_moderator()
@chunk_guild()
async def cmd_prune(ctx, flags):
    """
    Usage``:
        {prefix}prune [number] [flags] [--after <msgid>] [--from <user>] [-r <reason>]
    Description:
        Deletes your command message and messages from the given number of messages before that.
        If neither the number nor `after` is given, deletes from the last 100 messages.

        The flags restrict what types of messages are deleted from this collection.
        If there are multiple flags, only messages matching all the criteria will be deleted.

        To use this command, you need to be a **guild moderator**.\
            That is, you need to have the `manage_guild` permission or the configured `modrole`.

        **Note:** The modlog feature is currently temporarily disabled, so purges will not appear\
            in the modlog until it is reactivated (in the next release).
    Behavioural flags::
        r: Reason for the message purge.
        force: Force a prune without asking for a reason or confirmation.
    Restriction flags::
        bot: Only messages from bots.
        user:  Only messages from non-bots.
        embed:  Only messages with embeds (including link previews).
        file: Only messages with uploaded attachements (e.g. images).
        me: Only messages from me ({ctx.client.user.mention}).
        from: Only messages from the given user (interactive lookup).
        after: Only messages after (not including) the given message id (must be in the last `1000` messages).
    Examples``:
        {prefix}prune 100 --file
        {prefix}prune --after {ctx.msg.id}
        {prefix}prune 10 --me --embed
        {prefix}prune 10 --from {ctx.author.name} --image --force
    """
    # TODO: --before
    # TODO: --role? Maybe?
    # TODO: find_user won't work for users not in the server. Construct a collection based on message list.

    # First check that we have the permissions we need in the channel.
    perms = ctx.ch.permissions_for(ctx.guild.me)
    if not perms.manage_messages or not perms.read_message_history:
        return await ctx.error_reply(
            "I lack the `MANAGE MESSAGES` and `READ MESSAGE HISTORY` permissions I require to purge."
        )

    # Get the after message id from the flag, if provided
    after_msg_id = None
    if flags['after']:
        if flags['after'] is True or not flags['after'].isdigit():
            return await ctx.error_reply("**Usage:** {}purge ... --after <msgid> ...".format(ctx.best_prefix()))

        after_msg_id = int(flags['after'])

    # Get the maximum number of messages to search
    if not ctx.args:
        number = 1000 if after_msg_id is not None else 100
    elif not ctx.args.isdigit():
        await ctx.reply("Please give me a valid number of messages to delete. See the help for this command for usage.")
        return
    else:
        number = int(ctx.args)

    # Retrieve the user from the flag if provided
    user = None
    if flags["from"]:
        user = await ctx.find_member(flags["from"], interactive=True)
        if user is None:
            return await ctx.error_reply("Couldn't find the requested user, cancelling purge.")

    # Retrieve the reason from the flag, or request it
    if flags['r'] is True or not flags["r"]:
        if flags['force']:
            reason = "None, forced prune."
        else:
            try:
                reason = await ctx.input("Please enter a reason for this purge, or `c` to cancel.")
            except ResponseTimedOut:
                raise ResponseTimedOut("Reason prompt timed out, cancelling purge.") from None
            if reason.lower() == 'c':
                raise UserCancelled("Moderator cancelled the reason prompt, cancelling purge.")

            if not reason:
                return await ctx.error_reply("No reason provided, cancelling purge.")
    else:
        reason = flags['r']

    # Attempt to delete the sending message to ensure we have some permissions
    try:
        await ctx.msg.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        return await ctx.error_reply(
            "I do not have permissions to delete messages here.\n"
            "If this is in error, please give me the `MANAGE MESSAGES` permission."
        )

    # Start going through the channel history, counting messages
    count_dict = {"bots": {}, "users": {}}
    message_list = []
    msg_found = False

    async for message in ctx.ch.history(limit=number):
        if message.id == after_msg_id:
            msg_found = True
            break

        # Check whether we should delete this message
        to_delete = True
        to_delete = to_delete and (not (flags["bot"] or flags["bots"]) or message.author.bot)
        to_delete = to_delete and (not flags["user"] or not message.author.bot)
        to_delete = to_delete and (not flags["embed"] or message.embeds)
        to_delete = to_delete and (not flags["file"] or message.attachments)
        to_delete = to_delete and (not flags["from"] or message.author == user)
        to_delete = to_delete and (not flags["me"] or message.author == ctx.client.user)

        if to_delete:
            message_list.append(message)
            listing = count_dict["bots" if message.author.bot else "users"]
            if message.author.id not in listing:
                listing[message.author.id] = {"count": 0,
                                              "name": "{}".format(message.author)}
            listing[message.author.id]["count"] += 1

    if after_msg_id and not msg_found:
        return await ctx.reply("The given message wasn't found in the last {} messages".format(number))

    if not message_list:
        return await ctx.error_reply("No messages matching the given criteria were found!")

    bot_lines = "\n".join(
        ["\t**{name}** ({key}): ***{count}*** messages".format(**count_dict["bots"][key], key=key)
         for key in count_dict["bots"]]
    )
    user_lines = "\n".join(
        ["\t**{name}** ({key}): ***{count}*** messages".format(**count_dict["users"][key], key=key)
         for key in count_dict["users"]]
    )
    bot_counts = "__**Bots**__\n{}".format(bot_lines) if bot_lines else ""
    user_counts = "__**Users**__\n{}".format(user_lines) if user_lines else ""
    counts = "{}\n{}".format(bot_counts, user_counts)
    abort = False
    if not flags["force"]:
        out_msg = await ctx.reply(
            "Purging **{}** messages. Message Breakdown:\n"
            "{}\n--------------------\n"
            "Please type `confirm` to delete the above messages or `abort` to abort now.".format(
                len(message_list), counts
            )
        )
        try:
            reply_msg = await ctx.listen_for(allowed_input=["abort", "confirm"], timeout=60)
        except ResponseTimedOut:
            await ctx.error_reply("Purge confirmation request timed out, cancelling purge.")
            abort = True
        else:
            if reply_msg.content.lower() == "abort":
                await ctx.error_reply("Moderator cancelled message purge.")
                abort = True
        finally:
            try:
                await reply_msg.delete()
            except Exception:
                pass

    if not abort:
        try:
            if not flags["force"]:
                await out_msg.delete()

            if len(message_list) == 1:
                await message_list[0].delete()
            else:
                msgids = [msg.id for msg in message_list]
                await ctx.ch.purge(limit=number, check=lambda msg: msg.id in msgids)
        except discord.Forbidden:
            await ctx.error_reply("I have insufficient permissions to delete these messages.")
            abort = True
        except discord.HTTPException:
            try:
                for msg in message_list:
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        # The message may have been deleted in the meantime
                        pass
            except discord.Forbidden:
                await ctx.reply("I have insufficient permissions to delete these messages.")
                abort = True
    if abort:
        return

    success = await ctx.reply("Purge complete.")
    try:
        await asyncio.sleep(3)
        await success.delete()
    except Exception:
        pass    

#    final_message = "Purged **{}** messages. Message breakdown:\n{}".format(len(message_list), counts)
#    await ctx.reply(final_message)

    # modlog posting should be integrated with mod commands
    # have a modlog method which makes an embed post labelled with time and moderator name.
#     modlog = await ctx.server_conf.modlog_ch.get(ctx)
#     if not modlog:
#         return
#     modlog = ctx.server.get_channel(modlog)
#     if not modlog:
#         return

#     embed = discord.Embed(title="Messages purged", color=discord.Colour.red(), description="**{}** messages purged in {}.".format(len(message_list), ctx.ch.mention))
#     embed.add_field(name="Message Breakdown", value=counts, inline=False)
#     embed.add_field(name="Reason", value=reason, inline=False)
#     embed.set_footer(icon_url=ctx.author.avatar_url, text=datetime.utcnow().strftime("Acting Moderator: {} at %I:%M %p, %d/%m/%Y".format(ctx.author)))
#     try:
#         await ctx.bot.send_message(modlog, embed=embed)
#     except discord.Forbidden:
#         await ctx.reply("Tried to post to the modlog but had insufficient permissions")
#     except Exception:
#         pass
