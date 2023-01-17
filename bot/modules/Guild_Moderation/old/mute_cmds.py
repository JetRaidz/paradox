import asyncio
import datetime
import discord

from paraCH import paraCH

from ModEvent import ModEvent
from mod_utils import mod_parse, test_action, multi_mod_action


cmds = paraCH()


async def make_muted(ctx):
    role = discord.utils.get(ctx.server.roles, name="Muted")
    if role:
        await ctx.server_conf.mute_role.set(ctx, role.id)
        await ctx.reply("Set Muted role to existing role named Muted. You can change this in the config.")
        return role

    out_msg = await ctx.reply("Creating Mute role, please wait...")
    role_name = "Muted"
    colour = discord.Colour.red()
    perms = discord.Permissions.none()
    perms.send_messages = False
    role = None
    overwrite = discord.PermissionOverwrite()
    overwrite.send_messages = False
    try:
        role = await ctx.bot.create_role(ctx.server, name=role_name, colour=colour, permissions=perms)
        hot_roles = [r.position for r in ctx.me.roles if r.permissions.manage_roles or r.permissions.administrator]
        if hot_roles:
            hot_position = max(hot_roles)
            await ctx.bot.move_role(ctx.server, role, hot_position - 1)
    except discord.Forbidden:
        hot_roles = None
    if hot_roles:
        for channel in ctx.server.channels:
            try:
                await ctx.bot.edit_channel_permissions(channel, role, overwrite)
            except discord.Forbidden:
                pass

        await ctx.server_conf.mute_role.set(ctx, role.id)
        await ctx.bot.edit_message(out_msg, "Created new Mute role Muted. Please check the permission restrictions are correct.")
        return role


async def mute(ctx, user, **kwargs):
    role = await ctx.server_conf.mute_role.get(ctx)
    if role:
        role = discord.utils.get(ctx.server.roles, id=role)
    if not role:
        role = await make_muted(ctx)
    if not role:
        return -1
    try:
        await ctx.bot.add_roles(user, role)
    except discord.Forbidden:
        return 1
    except Exception:
        return 2
    dur = kwargs.get("duration", None)
    if dur and dur.total_seconds():
        unmute_event = ModEvent(ctx, "unmute", ctx.author, [user], "Scheduled Unmute after " + ctx.strfdelta(dur))
        embed = await unmute_event.embedify()

        now = datetime.datetime.utcnow().timestamp()
        to_store = (user.id, now + dur.total_seconds(), embed.to_dict())
        scheduled_unmutes = (await ctx.data.servers_long.get(ctx.server.id, "unmutes")) or []
        scheduled_unmutes.append(to_store)
        await ctx.data.servers_long.set(ctx.server.id, "unmutes", scheduled_unmutes)

        asyncio.ensure_future(schedule_unmute(ctx.bot, ctx.server, user, dur.total_seconds(), role, embed))
    return 0


async def schedule_unmute(bot, server, user, dur, role, embed):
    # Wait for the specified duration
    await asyncio.sleep(dur)

    # Fire the unmute event
    try:
        await bot.remove_roles(user, role)
    except Exception:
        pass

    # Remove user from server unmute list
    scheduled_unmutes = await bot.data.servers_long.get(server.id, "unmutes")
    if scheduled_unmutes:
        scheduled_unmutes = [item for item in scheduled_unmutes if item[0] != user.id]
    await bot.data.servers_long.set(server.id, "unmutes", scheduled_unmutes)

    # Get the server modlog
    modlog = await bot.data.servers.get(server.id, "modlog_ch")
    if modlog:
        modlog = server.get_channel(modlog)
        if modlog:
            await bot.send_message(modlog, embed=embed)


async def unmute(ctx, user, **kwargs):
    role = await ctx.server_conf.mute_role.get(ctx)
    if role:
        role = discord.utils.get(ctx.server.roles, id=role)
    if not role:
        return -1
    try:
        await ctx.bot.remove_roles(user, role)
    except discord.Forbidden:
        return 1
    except Exception:
        return 2
    return 0


@cmds.cmd("mute",
          category="Moderation",
          short_help="Mutes users (WIP)")
@cmds.execute("flags", flags=["r==", "f", "t==", "m"])
@cmds.require("in_server")
@cmds.require("in_server_can_mute")
async def cmd_mute(ctx):
    """
    Usage:
        {prefix}mute user 1, user 2, user 3 [-r <reason>] [-f] [-t <time>]
    Description:
        Mutes the users listed with an optional reason.
        <Required>, [Optional]
    Flags:3
        -r::  **reason** Reason for the mute.
        -f::  **fake** Pretends to mute.
        -t::  **time** Optional time to mute for.
    Examples:
        {prefix}mute {msg.author.name} -r For jokes -t 1d, 2h, 10m
    """
    if ctx.arg_str.strip() == "":
        await ctx.reply("You must give me a user to mute!")
        return
    reason, users = await mod_parse(ctx, purge=False)
    if not reason:
        return
    dur = None
    if ctx.flags["t"]:
        dur = ctx.parse_dur(ctx.flags["t"])
        if not dur:
            await ctx.reply("Didn't understand the duration given. See the help for usage.")
            return

    action_func = test_action if ctx.flags["f"] else mute
    strings = {"action_name": "mute",
               "action_multi_name": "multi-mute",
               "start": "Muting... \n" if not dur else "Temp-Muting for `{}`... \n".format(ctx.strfdelta(dur)),
               "fail_unknown": "🚨 Encountered an unexpected fatal error muting `{user.name}`! Aborting sequence..."}
    strings["results"] = {0: "Muted `{user.name}`!",
                          1: "🚨 Failed to mute `{user.name}`! (Insufficient Permissions)",
                          -1: "Failed to find or create a mute role. Please set a mute role in config or ensure I have permissions to create it."}
    await multi_mod_action(ctx, users, action_func, strings, reason, duration=dur)


@cmds.cmd("unmute",
          category="Moderation",
          short_help="Unmutes users (WIP)")
@cmds.execute("flags", flags=["r==", "f", "m"])
@cmds.require("in_server")
@cmds.require("in_server_can_unmute")
async def cmd_unmute(ctx):
    """
    Usage:
        {prefix}unmute user 1, user 2, user 3 [-r <reason>] [-f]
    Description:
        Unmutes the users listed with an optional reason.
        <Required>, [Optional]
    Flags:3
        -r::  **reason** Reason for the unmute.
        -f::  **fake** Pretends to unmute.
    Examples:
        {prefix}unmute {msg.author.name} -r Jokes complete
    """
    if ctx.arg_str.strip() == "":
        await ctx.reply("You must give me at least one user to unmute")
        return
    reason, users = await mod_parse(ctx, purge=False)
    if not reason:
        return

    action_func = test_action if ctx.flags["f"] else unmute
    strings = {"action_name": "unmute",
               "action_multi_name": "multi-unmute",
               "start": "Unmuting... \n",
               "fail_unknown": "🚨 Encountered an unexpected fatal error unmuting `{user.name}`! Aborting sequence..."}
    strings["results"] = {0: "Unmuted `{user.name}`!",
                          1: "🚨 Failed to unmute `{user.name}`! (Insufficient Permissions)",
                          -1: "Failed to find a mute role."}
    await multi_mod_action(ctx, users, action_func, strings, reason)


async def register_scheduled_unmutes(bot):
    scheduled = 0

    for server in bot.servers:
        unmutes = await bot.data.servers_long.get(server.id, "unmutes")
        if unmutes:
            muteroleid = await bot.data.servers.get(server.id, "mute_role")
            muterole = discord.utils.get(server.roles, id=muteroleid) if muteroleid else None
            if not muterole:
                await bot.data.servers_long.set(server.id, "unmutes", None)
            else:
                for uid, ts, embed_dict in unmutes:
                    member = server.get_member(uid)
                    if not member:
                        continue
                    dur = ts - datetime.datetime.utcnow().timestamp()
                    dur = dur if dur > 0 else 1
                    embed = discord.Embed.from_data(embed_dict)
                    scheduled += 1
                    asyncio.ensure_future(schedule_unmute(bot, server, member, dur, muterole, embed))

    await bot.log("Scheduled {} users to unmute.".format(scheduled))


async def add_mute_perm(bot, channel):
    server = channel.server

    muteroleid = await bot.data.servers.get(server.id, "mute_role")
    muterole = discord.utils.get(server.roles, id=muteroleid) if muteroleid else None
    if not muterole:
        return

    overwrite = discord.PermissionOverwrite()
    overwrite.send_messages = False
    try:
        await bot.edit_channel_permissions(channel, muterole, overwrite)
    except discord.Forbidden:
        pass


def load_into(bot):
    bot.data.servers.ensure_exists("muted_role", "mod_role", shared=True)
    bot.data.servers_long.ensure_exists("unmutes", shared=False)

    bot.add_after_event("ready", register_scheduled_unmutes)
