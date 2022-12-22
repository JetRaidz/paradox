import discord
from discord import Status
from discord.http import Route

from cmdClient import Context

from wards import in_guild, chunk_guild
from constants import ParaCC
from utils.lib import emb_add_fields, paginate_list, strfdelta, prop_tabulate, join_list

from .module import info_module as module

# Provides serverinfo, userinfo, roleinfo, whohas, avatar
"""
Provides a number of information lookup commands on Discord objects

Commands provided:
    userinfo:
        Provides info on the provided user
    avatar:
        Displays the avatar for the provided user
    role:
        Displays info on the provided role, or displays a list of roles
    rolemembers:
        Displays the members of a role
    serverinfo:
        Displays info on the current server
    channelinfo:
        Displays information about a specified channel
"""


async def get_server_avatar(ctx, gid, uid):
    """
    Fetches a member's server avatar URL, and return it if it exists.
    If the member does not have a server avatar, None will be returned.

    Parameters
    ----------
    gid: int
        The guild ID.
    uid: int
        The member's user ID.  

    Returns: str
        The direct URL to the member's server avatar.

    """

    res = await ctx.client.http.request(Route("GET", f"/guilds/{gid}/members/{uid}"))
    
    if not res["avatar"]:
        return None

    if res["avatar"].startswith("a_"):
        filetype = "gif"
    else:
        filetype = "png"

    url = f"https://cdn.discordapp.com/guilds/{gid}/users/{uid}/avatars/{res['avatar']}.{filetype}?size=1024"
    return url


async def get_user_banner(ctx, uid):
    """
    Fetches a user's profile banner, and return it if it exists.
    If the member does not have a profile banner, None will be returned.

    Parameters
    ----------
    uid: int
        The user's ID.  

    Returns: str
        The direct URL to the user's profile banner.

    """

    res = await ctx.client.http.request(Route("GET", f"/users/{uid}"))
    if not res["banner"]:
        return None

    if res["banner"].startswith("a_"):
        filetype = "gif"
    else:
        filetype = "png"

    url = f"https://cdn.discordapp.com/banners/{uid}/{res['banner']}.{filetype}?size=2048"
    return url


@module.cmd(name="roleinfo",
            desc="Displays information about a role.",
            aliases=["role", "rinfo", "ri"])
@in_guild()
@chunk_guild()
async def cmd_roleinfo(ctx: Context):
    """
    Usage``:
        {prefix}roleinfo [<role-name> | <role-mention> | <role-id>]
    Description:
        Provides information about the given role.
        If no role is provided, all of the roles in the guild will be listed.
    """
    # Get a sorted list of guild roles by position
    guild_roles = sorted(ctx.guild.roles, key=lambda role: role.position)

    # Handle not having arguments, list all the current roles
    if not ctx.args:
        await ctx.pager(paginate_list([role.name for role in reversed(guild_roles)], title="Guild roles"))
        return
    role = await ctx.find_role(ctx.args, create=False, interactive=True)
    if not role:
        return

    # Prepare the role properties
    colour = role.colour if role.colour.value else discord.Colour.light_grey()
    num_users = len(role.members)
    created = role.created_at.strftime("%I:%M %p, %d/%m/%Y")
    created_ago = "({} ago)".format(strfdelta(discord.utils.utcnow() - role.created_at, minutes=True))
    hoisted = "Yes" if role.hoist else "No"
    mentionable = "Yes" if role.mentionable else "No"

    # Build the property/value table
    prop_list = ["Colour", "Hoisted", "Mentionable", "Number of members", "Created at", ""]
    value_list = [str(role.colour), hoisted, mentionable, num_users, created, created_ago]
    desc = prop_tabulate(prop_list, value_list)

    # Build the hierarchy graph
    pos = role.position
    position = "```markdown\n"
    for i in reversed(range(-3, 4)):
        line_pos = pos + i
        if line_pos < 0:
            break
        if line_pos >= len(guild_roles):
            continue
        position += "{:>4}.   {} {}\n".format(
            len(guild_roles) - line_pos,
            ">" if guild_roles[line_pos] == role else " ",
            guild_roles[line_pos]
        )

    # Build the relative string
    position += "```"
    if not ctx.guild.default_role == ctx.author.top_role:
        if role > ctx.author.top_role:
            diff_str = "(This role is above your highest role.)"
        elif role < ctx.author.top_role:
            diff_str = "(This role is below your highest role.)"
        elif role == ctx.author.top_role:
            diff_str = "(This is your highest role!)"
        position += diff_str

    # Finally, build the embed and reply
    title = f"{role.name} ({role.id})"
    embed = discord.Embed(title=title, colour=colour, description=desc)
    emb_fields = [("Position in the hierarchy", position, 0)]
    emb_add_fields(embed, emb_fields)
    await ctx.reply(embed=embed)


@module.cmd(name="rolemembers",
            desc="Lists members with a particular role.",
            aliases=["rolemems", "whohas"])
@in_guild()
@chunk_guild()
async def cmd_rolemembers(ctx: Context):
    """
    Usage``:
        {prefix}rolemembers [<role-name> | <role-mention> | <role-id> | <partial lookup>]
    Description:
        Lists all of the users in the specified role.
     """
    if not ctx.args:
        return await ctx.error_reply("Please provide a role to list the members of.")

    role = await ctx.find_role(ctx.args, create=False, interactive=True)
    if not role:
        return

    members = role.members
    if len(members) == 0:
        await ctx.reply("No members have this role.")
        return
    await ctx.pager(paginate_list(members, title="Members in {}".format(role.name)))


@module.cmd("userinfo",
            desc="Shows various information about a user.",
            aliases=["uinfo", "ui", "user", "profile"])
@in_guild()
@chunk_guild()
async def cmd_userinfo(ctx: Context):
    """
    Usage``:
        {prefix}userinfo [user]
    Description:
        Sends information on the provided user.
        If no user is provided, the author will be used.
    """

    user = ctx.author
    if ctx.args:
        user = await ctx.find_member(ctx.args, interactive=True)
        if not user:
            return

    colour = (user.colour if user.colour.value else ParaCC["blue"])

    name = "{} {}".format(user, ctx.client.conf.emojis.getemoji("bot") if user.bot else "")

    banner = await get_user_banner(ctx, user.id)
    serverav = await get_server_avatar(ctx, ctx.guild.id, user.id)

    numshared = sum(g.get_member(user.id) is not None for g in ctx.client.guilds)
    shared = "{} guild{}".format(numshared, "s" if numshared > 1 else "")
    joined = int(round(user.joined_at.timestamp()))
    joined_ago = f"<t:{joined}:F>"
    created = int(round(user.created_at.timestamp()))
    created_ago = f"<t:{created}:F>"
    prop_list = ["Full name", "Nickname", "Seen in", "Joined at", "Created at"]
    value_list = [name, user.display_name,
                  shared, joined_ago, created_ago]
    desc = prop_tabulate(prop_list, value_list)

    roles = [r.name for r in reversed(user.roles) if r.name != "@everyone"]
    roles = ('`' + '`, `'.join(roles) + '`') if roles else "None"

    embed = discord.Embed(color=colour, description=desc)
    embed.set_author(name=f"{user} ({user.id})",
                     icon_url=user.display_avatar)
    if serverav:
        embed.set_thumbnail(url=serverav)
    else:
        embed.set_thumbnail(url=user.display_avatar)

    embed.add_field(name="Roles", value=roles, inline=False)

    if banner:
        embed.set_image(url=banner)

    if user.joined_at:  # joined_at is Optional
        joined = sorted((mem for mem in ctx.guild.members if mem.joined_at), key=lambda mem: mem.joined_at)
        pos = joined.index(user)
        positions = []
        for i in range(-3, 4):
            line_pos = pos + i
            if line_pos < 0:
                continue
            if line_pos >= len(joined):
                break
            positions.append(
                "{:>4}.   {} {}".format(
                   line_pos + 1, ">" if joined[line_pos] == user else " ",
                    joined[line_pos]
                )
            )
        join_seq = "```markdown\n{}\n```".format("\n".join(positions))
        embed.add_field(name="Join order", value=join_seq, inline=False)

    await ctx.reply(embed=embed)


@module.cmd("guildinfo",
            desc="Shows information about the guild.",
            aliases=["serverinfo", "sinfo", "si", "gi"],
            flags=["icon"])
@in_guild()
async def cmd_guildinfo(ctx: Context, flags):
    """
    Usage``:
        {prefix}guildinfo [--icon]
    Description:
        Shows information about the guild you are in.
    Flags::
        icon: Sends the guild icon in an embed.
    """
    guild = ctx.guild

    if flags["icon"]:
        if not ctx.guild.icon:
            return await ctx.reply("The current guild has no custom icon set.")
        embed = discord.Embed(color=discord.Colour.light_grey())
        embed.set_image(url=guild.icon)
        return await ctx.reply(embed=embed)

    verif_descs = {
        "none": "Unrestricted",
        "low": "Must have a verified email",
        "medium": "Must be registered for more than 5 minutes",
        "high": "Must be a member for more than 10 minutes",
        "extreme": "Must have a verified phone number",
    }

    verif_level = guild.verification_level.name
    ver = "{} | {}".format(verif_level.title(), verif_descs[verif_level])

    text = len(guild.text_channels)
    voice = len(guild.voice_channels)
    category = len(guild.categories)
    stage = len(guild.stage_channels)
    forum = len(guild.forums)
    total = len(guild.channels)
    bots = sum(m.bot for m in guild.members)
    humans = guild.member_count - bots
    members = "{} human{}, {} bot{} | {} total".format(humans, "s" if humans > 1 else "", 
                                                     bots, "s" if bots > 1 else "", guild.member_count)

    # Fetch guild owner without chunking entire guild
    if guild.owner_id:
        oid = guild.owner_id
        owner = await guild.fetch_member(oid)
        colour = owner.colour if owner.colour.value else discord.Colour.teal()
        owner = "{0} ({0.id})".format(owner)
    else:
        owner = "Unknown"
        colour = discord.Colour.teal()

    if guild.icon:
        icon = "[Icon Link]({})".format(guild.icon)
    else:
        icon = "No guild icon set"
    mfa = "Enabled" if guild.mfa_level else "Disabled"
    channels = "{} text, {} voice, {} categor{}, {} stage, {} forum | {} total".format(text, voice, category, "ies" if category > 1 else "y", stage, forum, total)
    boosts = "Level {} | {} boost{} total".format(guild.premium_tier, guild.premium_subscription_count, "" if guild.premium_subscription_count == 1 else "s")
    created = int(round(guild.created_at.timestamp()))
    created_ago = f"<t:{created}:F>"

    prop_list = ["Owner", "Icon", "Verification",
                 "2FA", "Roles", "Members", "Channels", "Server Boosts", "Created at"]
    value_list = [owner,
                  icon,
                  ver,
                  mfa,
                  len(guild.roles),
                  members, channels, boosts, created_ago]
    desc = prop_tabulate(prop_list, value_list)

    embed = discord.Embed(
        color=colour,
        description=desc
    )
    embed.set_author(name="{0} ({0.id})".format(ctx.guild))
    embed.set_thumbnail(url=guild.icon)

    """
    emb_fields = [("Member Status", status, 0), ("Member Status by Device", devicestatus, 0)]

    emb_add_fields(embed, emb_fields)
    """
    await ctx.reply(embed=embed)


@module.cmd("channelinfo",
            desc="Displays information about a channel.",
            aliases=["ci"],
            flags=["topic"])
@in_guild()
async def cmd_channelinfo(ctx: Context, flags):
    """
    Usage``:
        {prefix}channelinfo [<channel-name> | <channel-mention> | <channel-id] [--topic]
    Description:
        Gives information on a text channel, voice channel, or category.
        If no channel is provided, the current channel will be used.
    Flags::
        topic: Reply with only the channel topic.
    """
    tv = {
        "text": "Text channel",
        "voice": "Voice channel",
        "category": "Category",
        "news": "Announcement channel",
        "stage_voice": "Stage channel",
        "news_thread": "News thread",
        "public_thread": "Public thread",
        "private_thread": "Private thread",
        "forum": "Forum channel"
    }

    # Definitions to shorten the character count
    gch = []

    for ch in ctx.guild.channels:
        gch.append(ch)

    for ch in ctx.guild.threads:
        gch.append(ch)
    
    me = ctx.guild.me
    user = ctx.author
    # Disallow selecting channels that the user and bot cannot see.
    valid = [ch for ch in gch if (ch.permissions_for(user).read_messages) and (ch.permissions_for(me).read_messages)]
    ch = ctx.ch

    if ctx.args:
        ch = await ctx.find_channel(ctx.args, interactive=True, collection=valid)
        if not ch:
            return

    if flags['topic']:
        if isinstance(ch, (discord.TextChannel, discord.StageChannel, discord.ForumChannel)):
            return await ctx.reply(
                f"**Channel topic for {ch.mention}**:\n{ch.topic}"
                if ch.topic else f"{ch.mention} doesn't have a topic.", allowed_mentions=discord.AllowedMentions.none())
        else:
            return await ctx.reply("This channel type doesn't have a topic!")

    # Generic embed info, valid for every channel type.
    name = f"{ch.name} [{ch.mention}]" if not isinstance(ch, discord.CategoryChannel) else ch.name
    created = ch.created_at.strftime("%d/%m/%Y")
    created_ago = f"({strfdelta(discord.utils.utcnow() - ch.created_at, minutes=True)} ago)"

    category = "{0} ({0.id})".format(ch.category) if ch.category else "None"

    embed = discord.Embed(color=ParaCC["blue"])
    embed.set_author(name=f"Channel information for {ch.name}.")

    if isinstance(ch, discord.TextChannel):
        topic = ch.topic or "No topic."
        nsfw = "Yes" if ch.nsfw else "No"
        prop_list = ["Name", "Type", "ID", "NSFW", "Category", "Created at", ""]
        value_list = [name, tv[str(ch.type)], ch.id, nsfw, category, created, created_ago]

        if len(topic) > 30:
            embed.add_field(name="Topic", value=topic)
        else:
            prop_list.append("Topic")
            value_list.append(topic)
    elif isinstance(ch, discord.VoiceChannel):
        userlimit = ch.user_limit or "Unlimited"
        nsfw = "Yes" if ch.nsfw else "No"
        prop_list = ["Name", "Type", "ID", "NSFW", "Category", "Created at", "", "User limit"]
        value_list = [name, tv[str(ch.type)], ch.id, nsfw, category, created, created_ago, userlimit]

        # List current members.
        if ch.members:
            mems = "\n".join(f'{mem} ({mem.id})' for mem in ch.members)
            members = f"```{mems}```"
            field = [(f"Members: {len(ch.members)}", members, 0)]
            emb_add_fields(embed, field)
        else:
            embed.add_field(name="Members", value="None")
    elif isinstance(ch, discord.StageChannel):
        userlimit = ch.user_limit or "Unlimited"
        topic = ch.topic or "No topic."
        nsfw = "Yes" if ch.nsfw else "No"
        prop_list = ["Name", "Type", "ID", "NSFW", "Category", "Created at", "", "User limit"]
        value_list = [name, tv[str(ch.type)], ch.id, nsfw, category, created, created_ago, userlimit]

        if len(topic) > 30:
            embed.add_field(name="Topic", value=topic)
        else:
            prop_list.append("Topic")
            value_list.append(topic)

        if ch.speakers:
            mems = "\n".join(f'{mem} ({mem.id})' for mem in ch.speakers)
            speakers = f"```{mems}```"
            field = [(f"Speakers: {len(ch.speakers)}", speakers, 0)]
            emb_add_fields(embed, field)
        else:
            embed.add_field(name="Speakers", value="None")

        if ch.moderators:
            mems = "\n".join(f'{mem} ({mem.id})' for mem in ch.moderators)
            moderators = f"```{mems}```"
            field = [(f"Moderators: {len(ch.moderators)}", moderators, 0)]
            emb_add_fields(embed, field)
        else:
            embed.add_field(name="Moderators", value="None")

        if ch.listeners:
            mems = "\n".join(f'{mem} ({mem.id})' for mem in ch.listeners)
            listeners = f"```{mems}```"
            field = [(f"Listeners: {len(ch.listeners)}", listeners, 0)]
            emb_add_fields(embed, field)
        else:
            embed.add_field(name="Listeners", value="None")
    elif isinstance(ch, discord.Thread):
        # Embed info specific to threads.
        owner = ctx.guild.get_member(ch.owner_id)
        origin = "{} [<#{}>]".format(ctx.guild.get_channel(ch.parent_id), ch.parent_id)
        dur = int(ch.auto_archive_duration / 60)
        auto_archive = "In {} hour{}".format(dur, "s" if dur > 1 else "")
        archived = "Yes" if ch.archived else "No"
        last_modified = ch.archive_timestamp.strftime("%d/%m/%Y %H:%M:%S")
        tags = ", ".join(tag.name for tag in ch.applied_tags) if len(ch.applied_tags) else "No tags."

        prop_list = ["Name", "Origin", "Type", "ID", "Owner", "Auto archive", "Archived", "Last modified", "Tags"]
        value_list = [name, origin, tv[str(ch.type)], ch.id, owner, auto_archive, archived, last_modified, tags]
    elif isinstance(ch, discord.ForumChannel):
        nsfw = "Yes" if ch.nsfw else "No"
        tags = ", ".join(tag.name for tag in ch.available_tags) if len(ch.available_tags) else "No tags."
        prop_list = ["Name", "Type", "ID", "NSFW", "Created at", "", "Tags"]
        value_list = [name, tv[str(ch.type)], ch.id, nsfw, created, created_ago, tags]

        active = [thread for thread in ch.threads if not thread.archived]
        
        if active:
            thlist = ", ".join(thread.mention for thread in active)
            field = [(f"Active threads: {len(active)}", thlist, 0)]
            emb_add_fields(embed, field)

    elif isinstance(ch, discord.CategoryChannel):
        nsfw = "Yes" if ch.nsfw else "No"
        prop_list = ["Name", "Type", "ID", "NSFW", "Created at", ""]
        value_list = [name, tv[str(ch.type)], ch.id, nsfw, created, created_ago]

        # List visible channels in a category
        valid = [chan for chan in ch.channels if chan.permissions_for(ctx.author).read_messages]
        
        if valid:
            chlist = ", ".join(chan.mention for chan in valid)
            field = [(f"Channels under this category: {len(ch.channels)}", chlist, 0)]
            emb_add_fields(embed, field)
    else:
        # If any other type is present, provide generic information only.
        prop_list = ["Name", "Type", "ID", "Created at", ""]
        value_list = [name, tv[str(ch.type)], ch.id, created, created_ago]

    # Add the embed description
    desc = prop_tabulate(prop_list, value_list)
    embed.description = desc

    await ctx.reply(embed=embed)


@module.cmd("avatar",
            desc="Obtains the mentioned user's avatar, or your own.",
            aliases=["av"],
            flags=["server"])
async def cmd_avatar(ctx: Context, flags):
    """
    Usage``:
        {prefix}avatar [<username> | <user ID> | <user mention> | <partial lookup>] 
        [--server]
    Description:
        Displays the avatar of the provided user. If no user is provided, the author will be used.
        Hyperlinks the user's avatar so it can be viewed online.
    Flags::
        server: Display the user's server avatar, if set.
    """

    user = ctx.author
    if ctx.guild:
        if ctx.args:
            # Only chunk guild if arguments were provided
            await chunk_guild.run(ctx)

            user = await ctx.find_member(ctx.args, interactive=True)

            if not user:
                return
        if str(user.colour) == "#000000":
            colour = ParaCC["blue"]
        else:
            colour = user.colour
    else:
        colour = ParaCC["blue"]

    if flags["server"]:
        if not ctx.guild:
            return await ctx.error_reply("This flag can only be used in a server.")

        avatar = await get_server_avatar(ctx, ctx.guild.id, user.id)
        
        if not avatar:
            return await ctx.error_reply(f"{user} has no server avatar set.")

    else:
        avatar = user.display_avatar

    desc = f"Click [here]({avatar}) to view the {'GIF' if user.display_avatar.is_animated() else 'image'}."
    embed = discord.Embed(colour=colour, description=desc)
    embed.set_author(name=f"{user}'s Avatar")
    embed.set_image(url=avatar)

    await ctx.reply(embed=embed)
