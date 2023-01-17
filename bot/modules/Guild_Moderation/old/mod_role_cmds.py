import asyncio
import discord

from paraCH import paraCH

from mod_utils import role_finder, role_result, multi_action

cmds = paraCH()


async def giverole(ctx, role, **kwargs):
    user = kwargs["user"]
    try:
        await ctx.bot.add_roles(user, role)
    except discord.Forbidden:
        return 1
    except Exception:
        return 2
    return 0


@cmds.cmd("giverole",
          category="Moderation",
          short_help="Give role(s) to a member",
          aliases=["gr"])
@cmds.require("in_server")
@cmds.require("in_server_has_mod")
@cmds.execute("user_lookup", in_server=True)
async def cmd_giverole(ctx):
    """
    Usage:
        {prefix}giverole <user> <role1> [role2]...
    Description:
        Gives the specified roles to the provided user.
        Provides a friendlier alternative to {prefix}rolemod.
        <Required>, [Optional]
    Examples:
        {prefix}gr JetRaidz Member
    """
    if len(ctx.params) < 2:
        await ctx.reply("Please provide a user and at least one role to add.")
        return
    user = ctx.objs["found_user"]
    if not user:
        await ctx.reply("No users matching that criteria were found.")
        return
    await multi_action(ctx, ctx.params[1:], giverole, role_finder, role_result, "Adding Roles to `{}`...\n".format(user.name), user=user)


@cmds.cmd("rolemod",
          category="Moderation",
          short_help="Modify role(s) for member(s)!",
          aliases=["rmod"],
          flags=["add==", "remove=="])
@cmds.require("in_server")
@cmds.require("in_server_has_mod")
async def cmd_rolemod(ctx):
    """
    Usage:
        {prefix}rolemod user1, user2 --add role1, role2 --remove role3
        {prefix}rolemod user1, user2 +role1, role2 -role3
    Description:
        Modifies the specified user(s) roles.
        Roles may be specified either as flag arguments or after + or -.
    Example:
        {prefix}rmod {msg.author.name} --add Owner, root --remove bots, member
        {prefix}rmod {msg.author.name} +Owner, root -bots, member
    """
    if ctx.flags['add'] or ctx.flags['remove']:
        userblock = ctx.arg_str
        addblock = ctx.flags['add']
        negblock = ctx.flags['remove']
    else:
        searchstr = ctx.arg_str + '+-'
        plusi = searchstr.index('+')
        remi = searchstr.index('-')
        mini = min(plusi, remi)

        userblock = searchstr[:mini]
        remainder = searchstr[mini+1:-2]

        if mini == plusi:
            addblock, _, negblock = remainder.partition('-')
        else:
            negblock, _, addblock = remainder.partition('+')

    users = [user.strip() for user in userblock.split(",") if user.strip()]
    rolestrs = [(1, role.strip()) for role in addblock.split(",")]
    rolestrs += [(-1, role.strip()) for role in negblock.split(",")]

    roles = []
    for x, rolestr in rolestrs:
        if not rolestr:
            continue
        role = await ctx.find_role(rolestr, create=True, interactive=True)
        if role is None:
            return
        if role > ctx.author.top_role:
            await ctx.reply("You cannot add or remove a role above your highest role!")
            return
        roles.append((x, role))

    if len(users) == 0:
        await ctx.reply("No users were detected!")
        return
    if len(roles) == 0:
        await ctx.reply("No roles matching that criteria were found.")
        return
    error_lines = ""
    intro = "Modifying roles...\n"
    real_users = []
    user_lines = []
    n = len(users)
    out_msg = await ctx.reply(intro)
    for role in roles:
        for i in range(n):
            started = False
            if i >= len(real_users):
                started = True
                user_lines.append("\tIdentifying `{}`".format(users[i]))
                await ctx.bot.edit_message(out_msg, "{}{}{}".format(intro, "\n".join(user_lines), error_lines))
                user = await ctx.find_user(users[i], in_server=True, interactive=True)
                real_users.append(user)
                if user is None:
                    if ctx.cmd_err[0] != -1:
                        user_lines[i] = "\t🚨 Couldn't find user `{}`, skipping".format(users[i])
                    else:
                        user_lines[i] = "\t🗑 User selection aborted for `{}`, skipping".format(users[i])
                        ctx.cmd_err = (0, "")
                    await ctx.bot.edit_message(out_msg, "{}{}{}".format(intro, "\n".join(user_lines), error_lines))
                    continue
            if real_users[i] is None:
                continue
            user = real_users[i]
            if started:
                user_lines[i] = "\tModified user `{}` with: ".format(user)
            try:
                if role[0] > 0:
                    await ctx.bot.add_roles(user, role[1])
                    user_lines[i] += "{}`+{}`".format("" if started else ", ", role[1].name)
                else:
                    await ctx.bot.remove_roles(user, role[1])
                    user_lines[i] += "{}`-{}`".format("" if started else ", ", role[1].name)
            except discord.Forbidden:
                if not error_lines:
                    error_lines = "\nErrors:\n"
                error_lines += ("\tI don't have permissions to {} `{}`!\n".format("add role `{}` to".format(role[1].name) if role[0] > 0 else "remove role `{}` from".format(role[1].name), user))
                await asyncio.sleep(1)
            await ctx.bot.edit_message(out_msg, "{}{}{}".format(intro, "\n".join(user_lines), error_lines))


def load_into(bot):
    bot.data.servers.ensure_exists("muted_role", "mod_role", shared=True)
