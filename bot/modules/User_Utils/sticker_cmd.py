from datetime import datetime

import discord

from cmdClient import cmdClient

from utils.lib import prop_tabulate

from .module import utils_module as module


@module.cmd("sticker",
            desc="Displays info about a sticker and shows an enlarged version.",
            aliases=["s", "se", "stickerinfo"],
            flags=['e'])
async def cmd_sticker(ctx: cmdClient, flags):
    """
    Usage``:
        {prefix}sticker [sticker_id | sticker_name] [-e]
        {prefix}s [sticker_id | sticker_name]
        {prefix}se [sticker_id | sticker_name]
    Description:
        Displays information about the provided sticker, and sends an enlarged version.
        When used as a reply to a message containing a sticker, that sticker is used.
        Otherwise, looks up the sticker by ID, then by name within the current guild.
        With no argument, lists all custom stickers in the current guild.
        If used as `se` or given with the `-e` flag, only the enlarged image is shown.
    Flags::
        e: Only show the enlarged sticker, with no other information.
    Examples``:
        {prefix}sticker
        {prefix}sticker 1234567890
        {prefix}s mySticker
    """
    prefix = ctx.best_prefix()
    enlarged_only = (ctx.alias == 'se') or flags['e']

    sticker = await _sticker_from_reply(ctx)

    if sticker is None and ctx.args:
        sticker = await _sticker_from_args(ctx, ctx.args.strip())
        if sticker is None:
            return await ctx.error_reply(
                "Couldn't find a sticker matching `{}`!".format(ctx.args.strip())
            )

    if sticker is None:
        if not ctx.guild:
            return await ctx.error_reply(
                "Reply to a message containing a sticker, "
                "or look one up with `{}sticker <id|name>`.".format(prefix)
            )
        return await _list_guild_stickers(ctx)

    if enlarged_only:
        embed = discord.Embed(colour=discord.Colour.light_grey())
        embed.set_image(url=sticker.url)
        return await ctx.reply(embed=embed)

    prop_list, value_list = _sticker_info(ctx, sticker)
    desc = prop_tabulate(prop_list, value_list)
    embed = discord.Embed(color=discord.Colour.light_grey(),
                          description=desc,
                          title="Sticker info!")
    embed.set_image(url=sticker.url)
    await ctx.reply(embed=embed)


async def _sticker_from_reply(ctx):
    """
    If the invoking message is a reply to a message containing a sticker,
    return the first sticker on that message. Otherwise return `None`.
    """
    ref = ctx.msg.reference
    if not ref:
        return None

    referenced = ref.resolved if isinstance(ref.resolved, discord.Message) else None
    if referenced is None and ref.message_id:
        try:
            referenced = await ctx.ch.fetch_message(ref.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    if not referenced or not referenced.stickers:
        return None

    # `referenced.stickers` is a list of lightweight StickerItems;
    # fetch the full object so we can show description/creator/etc.
    sticker_item = referenced.stickers[0]
    try:
        return await sticker_item.fetch()
    except (discord.NotFound, discord.HTTPException):
        # Fall back to the StickerItem so we can at least show name + image.
        return sticker_item


async def _sticker_from_args(ctx, arg):
    """
    Resolve `arg` as a sticker:
    1. If `arg` is numeric, treat as a global sticker ID.
    2. Otherwise, search guild stickers by exact, then partial, name match.
    """
    if arg.isdigit():
        try:
            return await ctx.client.fetch_sticker(int(arg))
        except discord.NotFound:
            pass
        except discord.HTTPException:
            pass

    if ctx.guild and ctx.guild.stickers:
        lower = arg.lower()
        return (
            discord.utils.find(lambda s: s.name.lower() == lower, ctx.guild.stickers)
            or discord.utils.find(lambda s: lower in s.name.lower(), ctx.guild.stickers)
        )

    return None


async def _list_guild_stickers(ctx):
    """Send a paginated list of the current guild's custom stickers."""
    stickers = ctx.guild.stickers
    if not stickers:
        return await ctx.error_reply("No custom stickers found in this guild!")

    lines = ["`{id}` {name}".format(id=s.id, name=s.name) for s in stickers]
    blocks = ["\n".join(lines[i:i + 10]) for i in range(0, len(lines), 10)]
    embeds = [discord.Embed(
        title="Custom stickers in this guild",
        description=block,
        colour=discord.Colour.light_grey(),
        timestamp=datetime.now()
    ) for block in blocks]
    await ctx.pager(embeds, locked=False)


def _sticker_info(ctx, sticker):
    """
    Build (prop_list, value_list) for the sticker info embed.

    Handles `GuildSticker`, `StandardSticker`, and the lightweight
    `StickerItem` fallback gracefully by only including fields the
    object actually exposes.
    """
    prop_list = ['Name', 'ID']
    value_list = [sticker.name, str(sticker.id)]

    fmt = getattr(sticker, 'format', None)
    if fmt is not None:
        prop_list.append('Format')
        value_list.append(fmt.name.upper())

    description = getattr(sticker, 'description', None)
    if description:
        prop_list.append('Description')
        value_list.append(description)

    # `emoji` on a GuildSticker is the related emoji shortcode (str).
    related_emoji = getattr(sticker, 'emoji', None)
    if related_emoji:
        prop_list.append('Related emoji')
        value_list.append(":{}:".format(related_emoji))

    if isinstance(sticker, discord.GuildSticker):
        if sticker.available is False:
            prop_list.append('Available')
            value_list.append('No')
        if sticker.guild:
            prop_list.append('Guild')
            value_list.append(sticker.guild.name)
        if sticker.user:
            prop_list.append('Creator')
            value_list.append(str(sticker.user))
    elif isinstance(sticker, discord.StandardSticker):
        prop_list.append('Pack ID')
        value_list.append(str(sticker.pack_id))

    created_at = getattr(sticker, 'created_at', None)
    if created_at is not None:
        prop_list.append('Created at')
        value_list.append(ctx.ts(created_at))

    prop_list.append('Image link')
    value_list.append('[Click here]({})'.format(sticker.url))

    return prop_list, value_list
