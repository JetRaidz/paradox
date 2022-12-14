import discord
from datetime import datetime

from cmdClient import cmdClient
import constants

from utils.lib import mail

from .module import bot_admin_module as module


"""
Event handlers for posting the leave/join guild messages in the guild log

Handlers:
    log_left_guild:
        Posts to the guild log when the bot leaves a guild
    log_joined_guild:
        Posts to the guild log when the bot joins a guild
"""


async def log_left_guild(client: cmdClient, guild: discord.Guild):
    # Build embed
    embed = discord.Embed(title="`{0.name} (ID: {0.id})`".format(guild),
                          colour=discord.Colour.red(),
                          timestamp=datetime.now())
    embed.set_author(name="Left guild!")
    embed.set_thumbnail(url=guild.icon_url)

    # Add more specific information about the guild
    embed.add_field(name="Owner", value="{0.name} (ID: {0.id})".format(guild.owner), inline=False)
    embed.add_field(name="Members (cached)", value="{}".format(len(guild.members)), inline=False)
    embed.add_field(name="Now chatting in", value="{} guilds".format(len(client.guilds)), inline=False)

    # Retrieve the guild log channel and log the event
    log_chid = client.conf.get("guild_log_ch")
    if log_chid:
        await mail(client, log_chid, embed=embed)


async def log_joined_guild(client, guild):
    owner = guild.owner
    icon = guild.icon.url

    bots = 0
    known = 0
    unknown = 0
    other_members = list(set([mem.id for mem in client.get_all_members() if mem.guild != guild]))

    for member in guild.members:
        if member.bot:
            bots += 1
        elif member.id in other_members:
            known += 1
        else:
            unknown += 1

    mem1 = "people I know" if known != 1 else "person I know"
    mem2 = "new friends" if unknown != 1 else "new friend"
    mem3 = "bots" if bots != 1 else "bot"
    mem4 = "total members"
    known = "`{}`".format(known)
    unknown = "`{}`".format(unknown)
    bots = "`{}`".format(bots)
    total = "`{}`".format(guild.member_count)
    mem_str = "{0:<5}\t{4},\n{1:<5}\t{5},\n{2:<5}\t{6}, and\n{3:<5}\t{7}.".format(
        known,
        unknown,
        bots,
        total,
        mem1,
        mem2,
        mem3,
        mem4
    )
    created = guild.created_at.strftime("%I:%M %p, %d/%m/%Y")

    embed = discord.Embed(
        title="`{0.name} (ID: {0.id})`".format(guild),
        colour=discord.Colour.green(),
        timestamp=datetime.now()
    )
    embed.set_author(name="Joined guild!")
    embed.set_thumbnail(url=icon)

    embed.add_field(name="Owner", value="{0} (ID: {0.id})".format(owner), inline=False)
    embed.add_field(name="Created at", value="{}".format(created), inline=False)
    embed.add_field(name="Members", value=mem_str, inline=False)
    embed.add_field(name="Now chatting in", value="{} guilds".format(len(client.guilds)), inline=False)

    # Retrieve the guild log channel and log the event
    log_chid = client.conf.get("guild_log_ch")
    if log_chid:
        await mail(client, log_chid, embed=embed)


@module.init_task
def attach_guild_events(client):
    client.add_after_event('guild_join', log_joined_guild)
    client.add_after_event('guild_remove', log_left_guild)
