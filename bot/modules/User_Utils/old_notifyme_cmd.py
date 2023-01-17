import asyncio
from string import punctuation as punc

import discord
from pytz import timezone

from paraCH import paraCH

cmds = paraCH()

skeleton = {
    "server": {"id": 0},
    "from": {"id": 0},
    "mentions": {"id": 0},
    "rolementions": {"id": 0},
    "contains": {"text": "", "whole_word": False, "case_insensitive": False},
    "in": {"id": ""}
}

punc_trans = str.maketrans(punc, " "*len(punc))


def wholeword_check(string, substring):
    return substring.strip() in string.translate(punc_trans).split()


def check_listen(user, checks, msg_ctx):
    result = True
    result = result and ("server" not in checks or msg_ctx.server.id == checks["server"]["id"])
    result = result and ("from" not in checks or msg_ctx.authid == checks["from"]["id"])
    result = result and ("in" not in checks or msg_ctx.ch.id == checks["in"]["id"])
    result = result and ("notbot" not in checks or not msg_ctx.author.bot)
    result = result and ("mentions" not in checks or checks["mentions"]["id"] in msg_ctx.msg.raw_mentions)
    result = result and ("rolementions" not in checks or checks["rolementions"]["id"] in msg_ctx.msg.raw_role_mentions)
    if "contains" in checks:
        content = msg_ctx.msg.content
        text = checks['contains']['text']
        if "case_insensitive" in checks["contains"]:
            content = content.lower()
            text = text.lower()

        contains_result = (text in content)
        contains_result = contains_result and ("whole_word" not in checks["contains"] or
                                               wholeword_check(content, text))
        result = result and contains_result
    return result


async def check_can_view(user, ctx):
    return ctx.ch.permissions_for(ctx.server.get_member(user.id)).read_messages


async def check_to_str(ctx, check, markdown=True):
    items = []
    if "server" in check:
        server = ctx.bot.get_server(check["server"]["id"])
        if not server:
            return "Invalid check"
        items.append("(Server {})".format(server.name))
    if "from" in check:
        items.append("(From {})".format(await ctx.bot.get_user_info(check["from"]["id"])))
    if "mentions" in check:
        items.append("(Mentions user {})".format(await ctx.bot.get_user_info(check["mentions"]["id"])))
    if "rolementions" in check:
        items.append("(Mentions role {})".format(discord.utils.get(server.roles, id=check["rolementions"]["id"])))
    if "contains" in check:
        extra = " as a whole word" if 'whole_word' in check['contains'] else ''
        extra += " (case insensitive)" if 'case_insensitive' in check['contains'] else '(case sensitive)'
        items.append("(Contains \"{}\"{})".format(check["contains"]["text"], extra))
    if "in" in check:
        items.append("(Channel {})".format(discord.utils.get(ctx.bot.get_all_channels, id=check["in"]["id"])))
    if "notbot" in check:
        items.append("(Not a bot)")
    if 'smart' in check:
        items.append("(Smart delay)")

    return (" **and** " if markdown else " and ").join(items)


async def build_trigger_from_flags(ctx, flags):
    """
    Build a trigger from a collection of input flags
    """
    trigger = {}

    # Option: smart or delay
    if flags['delay'] or flags['smart']:
        trigger['smart'] = True

    # Option: notbot
    if flags['notbot']:
        trigger['notbot'] = True

    # Option: here
    if flags['here']:
        trigger['server'] = {'id': ctx.server.id}

    # Option: in
    if flags['in']:
        # Interactively lookup the channel
        channel = await ctx.find_channel(flags['in'], interactive=True)
        if not channel:
            await ctx.reply("I couldn't find the specified channel!")
            return None
        trigger['channel'] = {'id': channel.id}

    # Option: from
    if flags['from']:
        # Special case
        if flags['from'] == 'me':
            user = ctx.author
        else:
            # Interactively lookup the user
            user = await ctx.find_user(flags['from'], interactive=True, in_server=True)
            if not user:
                await ctx.reply("I couldn't find the specified user!")
                return None
        trigger['from'] = {'id': user.id}

    # Option: mentions
    if flags['mentions']:
        # Special case
        if flags['mentions'] == 'me':
            user = ctx.author
        else:
            # Interactively lookup the user
            user = await ctx.find_user(flags['mentions'], interactive=True, in_server=True)
            if not user:
                await ctx.reply("I couldn't find the specified user!")
                return None
        trigger['mentions'] = {'id': user.id}

    # Option: rolementions
    if flags['rolementions']:
        # Interactively lookup the role
        role = await ctx.find_role(flags['rolementions'], interactive=True)
        if not role:
            await ctx.reply("I couldn't find the specified role!")
            return None
        trigger['rolementions'] = {'id': role.id}
        trigger['server'] = {'id': ctx.server.id}

    # Contains text
    if flags['contains']:
        trigger['contains'] = {'text': flags['contains'].strip('\"')}

        # Option: word
        if flags['word']:
            trigger['contains']['whole_word'] = True

        # Option: case_insensitive
        if flags['ignorecase']:
            trigger['contains']['case_insensitive'] = True

    return trigger


@cmds.cmd("notifyme",
          category="Utility",
          short_help="DMs you messages matching given criteria.",
          aliases=["tellme", "pounce", "listenfor", "notify"])
@cmds.execute("flags", flags=[
    "block", "unblock", "remove", "interactive",
    "smart", "delay",
    "mentions==", "contains==", "rolementions==",
    "from==", "in==", "here", "notbot", "word", "ignorecase"
])
async def cmd_notifyme(ctx):
    """
    Usage:
        {prefix}notifyme
        {prefix}notifyme [text] [options]
        {prefix}notifyme --mentions me
        {prefix}notifyme --remove
        {prefix}notifyme [--block | --unblock] <user>
    Description:
        Notifyme sends you a direct message whenever messages matching your criteria are detected.
        On its own, displays a list of current notification conditions.
        See Examples for examples of conditions.
        (WIP command, more soon)
    Options:8
        word:: Given `text` must appear as a word.
        ignorecase:: Case will be ignored when checking message content.
        here:: Message must be from this server.
        from:: Message must be from this specified user.
        notbot:: Message was not sent by a bot.
        in:: Message must be in this channel.
        mentions:: Message mentions provided user.
        rolementions:: Message mentions provided role.
        smart:: WIP option to delay notifications and not send them if you've already seen the message
    Flags:9
        remove:: Displays a menu where you can select a check to remove.
        block:: Don't get pounces from this user.
        unblock:: Get pounces from this user again after blocking them.
    Examples:
        {prefix}pounce --mentions me
        {prefix}pounce {msg.author.name} --notbot --word --smart --ignorecase
        {prefix}pounce --rolementions moderator
    """
    checks = await ctx.data.users_long.get(ctx.authid, "notifyme")
    checks = checks if checks else []

    if ctx.flags["remove"]:
        # Do interactive menu stuff
        if not checks:
            await ctx.reply("You haven't set any checks yet!")
        else:
            check_strs = []
            for check in checks:
                check_strs.append(await check_to_str(ctx, check, markdown=False))
            selected = await ctx.multi_selector("Select pounces to remove!", check_strs)
            if not selected:
                return
            to_remove = []
            for item in selected:
                to_remove.append(checks[item])
            for item in to_remove:
                checks.remove(item)
            await update_checks(ctx, checks)
            await ctx.reply("The selected pounce has been removed!")
    elif ctx.flags['block']:
        # Block user
        if not ctx.server:
            await ctx.reply("`--block` can only be used in servers.")
            return
        user = await ctx.find_user(ctx.arg_str, interactive=True, in_server=True)
        if not user:
            await ctx.reply("I couldn't find this user!")
            return

        blocklist = (await ctx.data.users_long.get(ctx.author.id, "pounce_blocks")) or []
        blocklist.append(user.id)
        await ctx.data.users_long.set(ctx.author.id, "pounce_blocks", blocklist)

        await ctx.reply("You will no longer recieve notifications triggered by this user!")
    elif ctx.flags['unblock']:
        # Unblock user
        if not ctx.server:
            await ctx.reply("`--unblock` can only be used in servers.")
            return

        user = await ctx.find_user(ctx.arg_str, interactive=True, in_server=True)
        if not user:
            await ctx.reply("I couldn't find this user!")
            return

        blocklist = (await ctx.data.users_long.get(ctx.author.id, "pounce_blocks")) or []
        if user.id not in blocklist:
            await ctx.reply("You haven't blocked this user!")
        else:
            blocklist.remove(user.id)
            await ctx.data.users_long.set(ctx.author.id, "pounce_blocks", blocklist)
            await ctx.reply("You will now recieve notifications triggered by this user!")
    elif any(ctx.flags[flag] for flag in ctx.flags) or ctx.arg_str:
        # Handle server only flags
        if not ctx.server and (ctx.flags["here"]
                               or ctx.flags["in"]
                               or ctx.flags["from"]
                               or ctx.flags["rolementions"]
                               or ctx.flags["mentions"]):
            await ctx.reply("You can only use these options in a server!")
            return

        # Move the argument string to the contains flag, if it exists
        if ctx.arg_str:
            ctx.flags["contains"] = ctx.arg_str

        # Build the check
        check = await build_trigger_from_flags(ctx, ctx.flags)
        if check is None:
            # Building the check failed, return silently
            return

        # Check if the trigger is already in our checks
        if check in checks:
            await ctx.reply("This trigger already exists!")
            return

        # Check if the trigger text is past the minimum threshold
        if ('mentions' not in check and 'rolementions' not in check) and not('contains' in check and len(check['contains']['text']) > 2):
            await ctx.reply("Your trigger must contain either a mention or trigger text at least 3 characters long.")
            return

        # Add to check list, register, and save
        checks.append(check)
        await update_checks(ctx, checks)
        await ctx.reply("Added pounce!")
    else:
        # Display current pounces and quit
        if not checks:
            prefix = (await ctx.bot.get_prefixes(ctx))[0]
            await ctx.reply(("You haven't set any triggers up yet!\n"
                            "See {}help notifyme for more information about setting triggers.".format(prefix)))
        else:
            check_strs = []
            for check in checks:
                check_strs.append(await check_to_str(ctx, check, markdown=False))
            await ctx.pager(ctx.paginate_list(check_strs, title="Current triggers"), dm=ctx.bot.objects["brief"])
            await ctx.confirm_sent(ctx.msg, "Sent your pounces")


async def update_checks(ctx, checks):
    await ctx.data.users_long.set(ctx.authid, "notifyme", checks)
    listeners = ctx.bot.objects["notifyme_listeners"]
    listener = listeners[ctx.authid] if ctx.authid in listeners else {"user": ctx.author}
    listener["checks"] = checks
    listeners[ctx.authid] = listener


async def set_timer(time, flag):
    """
    Small timer, waits for the amount of time then sets flag['expired'] to True
    """
    await asyncio.sleep(time)
    flag['expired'] = True


async def notify_user(user, ctx, check):
    # Check the user's blacklist
    blocklist = (await ctx.data.users_long.get(user.id, "pounce_blocks")) or []
    if ctx.author.id in blocklist:
        await ctx.log("User {} was blocked from notifying user {} ({}) with check {}".format(ctx.author.id, user, user.id, check), chid=ctx.ch.id)
        return

    # Get some history, if possible
    prior_msgs = [ctx.msg]
    async for msg in ctx.bot.logs_from(ctx.ch, limit=5, before=ctx.msg):
        prior_msgs.append(msg)

    msgs = list(reversed(prior_msgs))
    # If the trigger is smart, we want to wait and watch for a while
    if 'smart' in check and check['smart']:
        timeout = 60
        msgcount = 5

        timer = {'expired': False}
        asyncio.ensure_future(set_timer(timeout, timer))

        while msgcount > 0 and not timer['expired']:
            new_msg = await ctx.bot.wait_for_message(timeout=15, channel=ctx.ch)
            if new_msg:
                if new_msg.author.id == user.id:
                    return
                msgs.append(new_msg)
                msgcount -= 1

    tz = await ctx.data.users.get(user.id, "tz")
    TZ = timezone(tz) if tz else None

    await ctx.log("Notifying user {} ({}) with check {}".format(user, user.id, check), chid=ctx.ch.id)
    msg_lines = "\n".join([ctx.msg_string(msg, mask_link=False, line_break=False, tz=TZ) for msg in msgs])
    jump_link = ctx.msg_jumpto(ctx.msg)
    message = "**__Pounce fired__** by **{}** in channel **{}** of **{}**\nJump link: {}\n\n{}".format(ctx.msg.author, ctx.ch.name, ctx.server.name, jump_link, msg_lines)
    await ctx.send(user, message=message)


async def register_notifyme_listeners(bot):
    bot.objects["notifyme_listeners"] = {}
    active_listeners = await bot.data.users_long.find_not_empty("notifyme")
    notifyme_listeners = {}
    for listener in active_listeners:
        listener = str(listener)
        try:
            user = await bot.get_user_info(listener)
        except discord.NotFound:
            continue
        if not user:
            continue
        check_list = await bot.data.users_long.get(listener, "notifyme")
        notifyme_listeners[listener] = {"user": user, "checks": check_list}
    bot.objects["notifyme_listeners"] = notifyme_listeners


async def fire_listeners(ctx):
    if not ctx.server:
        return
    if not ctx.bot.objects.get("ready", False):
        return
    listeners = ctx.bot.objects["notifyme_listeners"]
    active_in_server = [user.id for user in ctx.server.members if user.id in listeners]
    for userid in active_in_server:
        listener = listeners[userid]
        for check in listener["checks"]:
            if not check_listen(listener["user"], check, ctx):
                continue
            if not await check_can_view(listener["user"], ctx):
                continue
            if ctx.author.id in [listener["user"].id, ctx.me.id]:
                continue
            asyncio.ensure_future(notify_user(listener["user"], ctx, check))
            break


def load_into(bot):
    bot.data.users_long.ensure_exists("notifyme", shared=False)

    bot.add_after_event("ready", register_notifyme_listeners)
    bot.after_ctx_message(fire_listeners)
