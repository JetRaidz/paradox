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
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    if guild.owner:
        owner = f"{guild.owner} (ID: {guild.owner.id})"
    else:
        owner = f"ID: {guild.owner_id}"

    # Add more specific information about the guild
    embed.add_field(name="Owner", value=owner, inline=False)
    embed.add_field(name="Members (cached)", value="{}".format(guild.member_count), inline=False)
    embed.add_field(name="Now chatting in", value="{} guilds".format(len(client.guilds)), inline=False)

    # Retrieve the guild log channel and log the event
    log_chid = client.conf.get("guild_log_ch")
    if log_chid:
        await mail(client, log_chid, embed=embed)


async def log_joined_guild(client, guild):
    created = guild.created_at.strftime("%I:%M %p, %d/%m/%Y")

    embed = discord.Embed(
        title="`{0.name} (ID: {0.id})`".format(guild),
        colour=discord.Colour.green(),
        timestamp=datetime.now()
    )
    embed.set_author(name="Joined guild!")
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    if guild.owner:
        owner = f"{guild.owner} (ID: {guild.owner.id})"
    else:
        owner = f"ID: {guild.owner_id}"

    embed.add_field(name="Owner", value=owner, inline=False)
    embed.add_field(name="Created at", value="{}".format(created), inline=False)
    embed.add_field(name="Members", value="{}".format(guild.member_count), inline=False)
    embed.add_field(name="Now chatting in", value="{} guilds".format(len(client.guilds)), inline=False)

    # Retrieve the guild log channel and log the event
    log_chid = client.conf.get("guild_log_ch")
    if log_chid:
        await mail(client, log_chid, embed=embed)


@module.init_task
def attach_guild_events(client):
    client.add_after_event('guild_join', log_joined_guild)
    client.add_after_event('guild_remove', log_left_guild)
