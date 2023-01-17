import discord

from paraCH import paraCH

from mod_utils import mod_parse, test_action, multi_mod_action, user_finder, ban_finder

cmds = paraCH()


async def ban(ctx, user, **kwargs):
    """
    Todo: on rewrite, make this post reason
    """
#    ban_reason = kwargs["ban_reason"]
    days = kwargs["days"]
    try:
        await ctx.bot.ban(user, int(days))
    except discord.Forbidden:
        return 1
    except Exception:
        return 2
    return 0


async def softban(ctx, user, **kwargs):
    """
    Todo: on rewrite, make this post reason
    """
#    ban_reason = kwargs["ban_reason"]
    days = kwargs["days"]
    try:
        await ctx.bot.ban(user, int(days))
        await ctx.bot.unban(ctx.server, user)
    except discord.Forbidden:
        return 1
    except Exception:
        return 2
    return 0


async def kick(ctx, user, **kwargs):
    try:
        await ctx.bot.kick(user)
    except discord.Forbidden:
        return 1
    except Exception:
        return 2
    return 0


async def unban(ctx, user, **kwargs):
    try:
        await ctx.bot.unban(ctx.server, user)
    except discord.Forbidden:
        return 1
    except Exception:
        return 2
    return 0


@cmds.cmd("hackban",
          category="Moderation",
          short_help="Hackbans users",
          aliases=["hb"])
@cmds.execute("flags", flags=["r==", "p=", "m", "f"])
@cmds.require("in_server")
@cmds.require("in_server_can_hackban")
async def cmd_hackban(ctx):
    """
    Usage:
        {prefix}hackban user 1, user 2, user 3,... [-r <reason>] [-f] [-p days]
    Description:
        Hackbans the users listed with an optional reason.
        Hackbanning allows you to ban without the user being in the server.
        This is not an interactive command, you provide a userid for the users you wish to ban.
        Multi hackban currently supports up to 20 users.
        <Required>, [Optional]
    Flags:3
        -r::  **reason**, reason for the ban
        -p::  **purge**, purge <days> days of message history. (1 day by default)
        -f::  **fake**, pretends to hackban.
    """
    if ctx.arg_str.strip() == "":
        await ctx.reply("You must give me a user to hackban!")
        return
    reason, users, purge_days = await mod_parse(ctx, purge_default="1")
    if not reason:
        return

    action_func = test_action if ctx.flags["f"] else ban
    strings = {"action_name": "hackban",
               "action_multi_name": "multi-hackban",
               "start": "Hackbanning... \n",
               "fail_unknown": "🚨 Encountered an unexpected fatal error hackbanning `{user.name}` (id: `{user.id}`)! Aborting hackban sequence..."}
    strings["results"] = {0: "✅ Successfully hackbanned `{user.name}` (id: `{user.id}`)" + (" and purged `{}` days of messages.".format(purge_days) if int(purge_days) > 0 else "!"),
                          1: "🚨 Failed to hackban `{user.name}` (id: `{user.id}`), insufficient permissions."}
    await multi_mod_action(ctx, users, action_func, strings, reason, finder=user_finder, days=int(purge_days), ban_reason="{}: {}".format(ctx.author, reason))


@cmds.cmd("unban",
          category="Moderation",
          short_help="Unbans users")
@cmds.execute("flags", flags=["r==", "m"])
@cmds.require("in_server")
@cmds.require("in_server_can_unban")
async def cmd_unban(ctx):
    """
    Usage:
        {prefix}unban user 1, user 2, user 3,... [-r <reason>]
    Description:
        Unbans the listed users with optional reason.
        Partial names are supported.
        <Required>, [Optional]
    Flags:3
        -r::  **reason** Reason for unbanning
    """
    if ctx.arg_str.strip() == "":
        await ctx.reply("You must provide a user to unban.")
        return
    reason, users = await mod_parse(ctx, purge=False)
    if not reason:
        return

    action_func = unban
    strings = {"action_name": "unban",
               "action_multi_name": "multi-unban",
               "start": "Unbanning... \n",
               "fail_unknown": "🚨 Encountered an unexpected fatal error unbanning `{user.name}` (id: `{user.id}`)! Aborting unban sequence..."}
    strings["results"] = {0: "✅ Successfully unbanned `{user.name}` (id: `{user.id}`).",
                          1: "🚨 Failed to unban `{user.name}` (id: `{user.id}`), insufficient permissions."}
    await multi_mod_action(ctx, users, action_func, strings, reason, finder=ban_finder, ban_reason="{}: {}".format(ctx.author, reason))


@cmds.cmd("ban",
          category="Moderation",
          short_help="Bans users",
          aliases=["b", "banne", "bean"])
@cmds.execute("flags", flags=["r==", "p=", "f", "m"])
@cmds.require("in_server")
@cmds.require("in_server_can_ban")
async def cmd_ban(ctx):
    """
    Usage:
        {prefix}ban user 1, user 2, user 3,... [-r <reason>] [-p <days>] [-f]
    Description:
        Bans the users listed with an optional reason.
        Partial names are supported.
        <Required>, [Optional]
    Flags:3
        -r::  **reason** Reason for the ban
        -p::  **purge** Purge <days> days of message history. (1 day by default)
        -f::  **fake** Pretends to ban.
    """
    if ctx.arg_str.strip() == "":
        await ctx.reply("You must provide a user to ban.")
        return
    reason, users, purge_days = await mod_parse(ctx)
    if not reason:
        return

    action_func = test_action if ctx.flags["f"] else ban
    strings = {"action_name": "ban",
               "action_multi_name": "multi-ban",
               "start": "Banning... \n",
               "fail_unknown": "🚨 Encountered an unexpected fatal error banning `{user.name}`! Aborting ban sequence..."}
    strings["results"] = {0: "✅ Successfully banned `{user.name}`" + (" and purged `{}` days of messages.".format(purge_days) if int(purge_days) > 0 else "!"),
                          1: "🚨 Failed to ban `{user.name}`, insufficient permissions."}
    await multi_mod_action(ctx, users, action_func, strings, reason, days=int(purge_days), ban_reason="{}: {}".format(ctx.author, reason))


@cmds.cmd("softban",
          category="Moderation",
          short_help="Softbans users",
          aliases=["sb"])
@cmds.execute("flags", flags=["r==", "p=", "f", "m"])
@cmds.require("in_server")
@cmds.require("in_server_can_softban")
async def cmd_softban(ctx):
    """
    Usage:
        {prefix}softban user 1, user 2, user 3,... [-r <reason>] [-p <days>] [-f]
    Description:
        Softbans (bans and unbans) the users listed with an optional reason.
        Partial names are supported.
        <Required>, [Optional]
    Flags:3
        -r::  **reason** Reason for the ban
        -p::  **purge** Purge <days> days of message history. (1 day by default)
        -f::  **fake** Pretends to softban.
    """
    if ctx.arg_str.strip() == "":
        await ctx.reply("You must provide a user to softban.")
        return
    reason, users, purge_days = await mod_parse(ctx, purge_default="1")
    if not reason:
        return

    action_func = test_action if ctx.flags["f"] else softban
    strings = {"action_name": "softban",
               "action_multi_name": "multi-softban",
               "start": "Softbanning... \n",
               "fail_unknown": "🚨 Encountered an unexpected fatal error softbanning `{user.name}`! Aborting softban sequence..."}
    strings["results"] = {0: "✅ Softbanned `{user.name}`" + " and purged `{}` days of messages.".format(purge_days),
                          1: "🚨 Failed to softban `{user.name}`, insufficient permissions."}
    await multi_mod_action(ctx, users, action_func, strings, reason, days=int(purge_days), ban_reason="{}: {}".format(ctx.author, reason))


@cmds.cmd("kick",
          category="Moderation",
          short_help="Kicks users",
          aliases=["k"])
@cmds.execute("flags", flags=["r==", "f", "m"])
@cmds.require("in_server")
@cmds.require("in_server_can_kick")
async def cmd_kick(ctx):
    """
    Usage:
        {prefix}kick user 1, user 2, user 3,... [-r <reason>] [-f]
    Description:
        Kicks the users listed with an optional reason.
        <Required>, [Optional]
    Flags:3
        -r::  **reason** Reason for the kick.
        -f::  **fake** Pretends to kick.
    """
    if ctx.arg_str.strip() == "":
        await ctx.reply("You must provide a user to kick.")
        return
    reason, users = await mod_parse(ctx, purge=False)
    if not reason:
        return

    action_func = test_action if ctx.flags["f"] else kick
    strings = {"action_name": "kick",
               "action_multi_name": "multi-kick",
               "start": "Kicking... \n",
               "fail_unknown": "🚨 Encountered an unexpected fatal error kicking `{user.name}`! Aborting kick sequence..."}
    strings["results"] = {0: "✅ Kicked `{user.name}`.",
                          1: "🚨 Failed to kick `{user.name}`, insufficient permissions."}
    await multi_mod_action(ctx, users, action_func, strings, reason)


def load_into(bot):
    bot.data.servers.ensure_exists("muted_role", "mod_role", shared=True)
