import sys
import platform
import psutil
# from datetime import datetime

import discord
from cmdClient import Context

from utils.lib import prop_tabulate
from utils.ctx_addons import best_prefix  # noqa

from .module import meta_module as module


"""
Commands providing basic meta information about the bot.

Commands provided:
    about:
        Sends an embed with the status of the bot process,
        and statistics about the current shard client.
    ping:
        Test the API round trip response time through message edits.
    invite:
        Reply with an invite link for the current app.
    support:
        Reply with an invite link to the support guild for the current app.
"""


@module.cmd("about",
            desc="Shard status and bot statistics.")
async def cmd_about(ctx: Context):
    """
    Usage``:
        {prefix}about
    Description:
        Sends an embed with basic statistics about the current shard, host, and bot process.
    """
    table_fields = []

    # Current developers
    current_devs = ctx.client.app_info["dev_list"]
    devs = []
    for devid in current_devs:
        try:
            dev = await ctx.client.fetch_user(devid)
            devs.append(str(dev))
        except Exception:
            devs.append(str(devid))

    dev_str = ", ".join(devs)
    table_fields.append(("Developers", dev_str))

    # Shards, guilds, and members
    if ctx.client.shard_count > 1:
        shard_str = "{} of {}".format(ctx.client.shard_id, ctx.client.shard_count)
        table_fields.append(("Shard", shard_str))

        guild_str = "{} (~{} total)".format(
            len(ctx.client.guilds),
            ctx.client.shard_count * len(ctx.client.guilds)
        )
        table_fields.append(("Shard guilds", guild_str))

        member_str = "{} (~{} total)".format(
            len(list(ctx.client.get_all_members())),
            ctx.client.shard_count * len(list(ctx.client.get_all_members()))
        )
        table_fields.append(("Shard members", member_str))
    else:
        table_fields.append(("Guilds", len(ctx.client.guilds)))
        table_fields.append(("Members", len(list(ctx.client.get_all_members()))))

    # Commands
    table_fields.append((
        "Commands",
        "{}, with {} command keywords".format(len(ctx.client.cmds), len(ctx.client.cmd_names))
    ))

    # Memory
    mem = psutil.virtual_memory()
    mem_str = "{0:.2f}GB used out of {1:.2f}GB ({mem.percent}%)".format(
        mem.used/(1024 ** 3), mem.total/(1024 ** 3), mem=mem
    )
    table_fields.append(("Memory", mem_str))

    # CPU Usage
    table_fields.append((
        "CPU Usage",
        "{}%".format(psutil.cpu_percent())
    ))

    # API version
    table_fields.append((
        "API version",
        "{} ({})".format(discord.__version__, discord.version_info[3])
    ))

    # Python version
    table_fields.append(("Py version", sys.version.split("\n")[0]))

    # Platform
    table_fields.append(("Platform", platform.platform()))

    # Tabulate
    fields, values = zip(*table_fields)
    table = prop_tabulate(fields, values)

    # Create info string for top of description
    info = ctx.client.app_info["info_str"].format(prefix=ctx.best_prefix())

    # Create link string for bottom of description
    links = ("[Support Server]({}), [Invite Me]({}), [Help keep me running!]({})".format(
        ctx.client.app_info["support_guild"],
        ctx.client.app_info["invite_link"],
        ctx.client.app_info["donate_link"]
    ))

    # Build embed
    desc = "{}\n{}\n{}".format(info, table, links)
    embed = discord.Embed(title="About Me", color=discord.Colour.red(), description=desc)

    # Finally, send embed
    await ctx.reply(embed=embed)


@module.cmd("ping",
            desc="Check heartbeat and API latency.",
            aliases=["pong"])
async def cmd_ping(ctx: Context):
    """
    Usage``:
        {prefix}ping
    Description:
        Test the API round trip response by editing a message.
        Also sends the websocket protocol latency (heartbeat).
    """
    # Edit a message and see how long it takes
    msg = await ctx.reply("Beep")
    msg = await msg.edit(content="Boop")
    latency = ((msg.edited_at - msg.created_at).microseconds) // 1000

    await msg.edit(content="Ping: `{}`ms.\nHeartbeat: `{:.0f}`ms.".format(latency, ctx.client.latency * 1000))


@module.cmd("invite",
            desc="Sends the bot's invite link",
            aliases=["inv"])
async def cmd_invite(ctx: Context):
    """
    Usage``:
        {prefix}invite
    Description:
         Replies with a link to invite me to your server.
    """
    await ctx.reply("Visit <{}> to invite me!".format(ctx.client.app_info["invite_link"]))


@module.cmd("support",
            desc="Sends the link to the bot guild")
async def cmd_support(ctx):
    """
    Usage``:
        {prefix}support
    Description:
        Sends the invite link to my support guild.
    """
    await ctx.reply("Join my support server: {}".format(ctx.client.app_info["support_guild"]))


@module.cmd("donate",
            desc="Donate to help keep the bot running")
async def cmd_donate(ctx):
    """
    Usage``:
        {prefix}donate
    Description:
        Support the developers by donating to help cover the costs to run the servers.
        Current methods are Patreon, PayPal, and Wise.
    """
    patreon = "<https://patreon.com/texit>"
    paypal = "<https://www.paypal.com/paypalme/puerosola>"
    wise = "<https://wise.com/share/adamw2287>"

    await ctx.reply("Help support the development of the bots and cover server costs "
                    "by donating through one of the following services:\n"
                    f"Patreon: {patreon}\n"
                    f"PayPal: {paypal}\n"
                    f"Wise: {wise}\n"
                    "Supporting us through Patreon will grant you exclusive perks in our support server.\n"
                    "You will also be able to use our premium features which will be added in a future update.\n"
                    "Thank you for your support ❤️")
