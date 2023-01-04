from datetime import datetime

import re
import asyncio
import discord

from cmdClient import cmdClient

from utils.lib import prop_tabulate, strfdelta

from .module import utils_module as module
from .emojis import emojis_by_name, emoji_names_by_unicode

default_emoji_url = "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/{}.png"


def get_custom_emoji(ctx, emoji_str):
    # Not valid emoji name or emoji id
    # Cross fingers and hope it is of form a:name:id, <a:name:id>, name:id, or <:name:id>
    # Give up otherwise
    if not re.match(r"^[A-Za-z0-9_]+$", emoji_str):
        id = re.search(r"\d+", emoji_str)
        if not id:
            return None
        id = int(id.group())
        return discord.utils.get(ctx.client.emojis, id=id)

    # Not valid emoji id
    # Priority: guild exact match > guild inexact match > exact match > inexact match
    if not emoji_str.isdigit():
        if ctx.guild:
            return discord.utils.find(lambda e: emoji_str.lower() == e.name.lower(), ctx.guild.emojis) or \
                discord.utils.find(lambda e: emoji_str.lower() in e.name.lower(), ctx.guild.emojis) or \
                discord.utils.find(lambda e: emoji_str.lower() == e.name.lower(), ctx.client.emojis) or \
                discord.utils.find(lambda e: emoji_str.lower() in e.name.lower(), ctx.client.emojis)
        else:
            return discord.utils.find(lambda e: emoji_str.lower() == e.name.lower(), ctx.client.emojis) or \
                discord.utils.find(lambda e: emoji_str.lower() in e.name.lower(), ctx.client.emojis)

    # Valid emoji id
    if ctx.guild:
        return discord.utils.get(ctx.guild.emojis, id=int(emoji_str)) or \
            discord.utils.get(ctx.client.emojis, id=int(emoji_str))
    else:
        return discord.utils.get(ctx.client.emojis, id=int(emoji_str))


def unicode_char_rep(uni):
    # 65039 is fe0f, doesn't play nicely with Twemoji
    return "-".join(f"{ord(c):X}".lower() for c in uni if ord(c) >= 128 and ord(c) != 65039)


@module.cmd("emoji",
            desc="Displays info about, searches for, and enlarges custom emojis",
            aliases=["e", "ee", "ree", "sree", "emote"],
            flags=['e', 'to==', 'up=='])
async def cmd_emoji(ctx: cmdClient, flags):
    """
    Usage``:
        {prefix}emoji <emoji> [-e]
        {prefix}ee <emoji>
        {prefix}ree <emoji>  [--to msgid | --up count]
        {prefix}sree <emoji>
    Description:
        Displays some information about the provided custom emoji, and sends an enlarged version.
        If the emoji isn't found, instead searches for the emoji amongst all the emojis I can see.
        If used as ee or given with -e flag, only shows the enlarged image.
        If used as ree, reacts with the emoji, and as sree, silently reacts.
        Built in emoji support is coming soon!
    Flags::
        e: Only shows the enlarged emoji, with no other information.
        to: Accepts a message id in the current channel to react to.
        up: Accepts a number of messages above yours to react to (default is `1`).
    Examples``:
        {prefix}e catThink
    """
    prefix = ctx.best_prefix()

    # Flags indicating what we want to do
    react_only = (ctx.alias in ['ree', 'sree'])
    enlarged_only = (ctx.alias == 'ee') or (flags['e'] and not react_only)
    info = (ctx.alias == 'emoji') and not enlarged_only

    # No arguments given and we aren't reacting
    if not ctx.args and not react_only:
        # List the current guild custom emojis
        if not ctx.guild:
            return await ctx.error_reply("Search for emojis using `{}emoji <emojistring>`".format(prefix))

        emojis = ctx.guild.emojis
            
        if not emojis:
            return await ctx.error_reply(
                "No custom emojis found in this guild!\n"
                "Use this command to search for custom emojis from my other guilds."
            )
                
        emojistrs = ["{}`{id}` {name}".format(
            str(e),
            id=e.id,
            name=e.name
        ) for e in emojis]
        blocks = ["\n".join(emojistrs[i:i+10]) for i in range(0, len(emojistrs), 10)]
        embeds = [discord.Embed(
            title="Custom emojis in this guild",
            description=block,
            colour=discord.Colour.light_grey(),
            timestamp=datetime.now()
        ) for block in blocks]
        return await ctx.pager(embeds, locked=False)

    # If there's no args now that means we're reacting, and default reaction is reeeeeee
    em_str = ctx.args.strip(":") or "reeeeeeeeeee"

    # Time to find the emoji.
    emoji = get_custom_emoji(ctx, em_str)
    emoji_is_custom = False
    # Make special chars into unicode representation by normal chars
    unicode = unicode_char_rep(em_str) if em_str else None
    # Find match in emojis if there were special chars
    if unicode:
        unicode = unicode if unicode in emoji_names_by_unicode else \
            next((u for u in emoji_names_by_unicode if unicode in u), None)
    # If there were no special chars, then there's a chance string the representation
    # was passed as an argument, e.g. ~e 1f468
    if not unicode:
        unicode = em_str if em_str in emoji_names_by_unicode else \
            next((u for u in emoji_names_by_unicode if em_str in u), None)

    if emoji:
        emoji_is_custom = True

        # Emoji currently not usable
        if not emoji.available:
            return await ctx.error_reply("Emoji is currently unavailable!")
    elif unicode:
        emoji = {
            "unicode": unicode,
            "shortcode": emoji_names_by_unicode[unicode],
            "emoji": emojis_by_name[emoji_names_by_unicode[unicode]],
            "url": default_emoji_url.format(unicode)
        }
    else:
        name = em_str if em_str in emojis_by_name else \
            next((n for n in emojis_by_name if em_str in n), None)

        if name:
            unicode = unicode_char_rep(emojis_by_name[name])
            emoji = {
                "unicode": unicode,
                "shortcode": name,
                "emoji": emojis_by_name[name],
                "url": default_emoji_url.format(unicode)
            }

    # Just in case we somehow came out with no emoji
    if emoji is None:
        return await ctx.error_reply("No matching emojis found!")

    # At this point, we should have enough of the emoji to do what is requested.
    # Start handling the different output cases.
    if react_only:
        react_message = None
        if ctx.guild and not ctx.ch.permissions_for(ctx.author).add_reactions:
            return await ctx.error_reply("You do not have permissions to add reactions here!")

        if ctx.guild and not ctx.ch.permissions_for(ctx.guild.me).add_reactions:
            return await ctx.error_reply("I do not have permissions to add reactions here!")

        # If a messageid to react to was specified, get it. Otherwise get the previous message in the channel.
        if flags['to']:
            if not flags['to'].isdigit():
                return await ctx.error_reply("`to` argument must be a message id.")
            react_message = await ctx.ch.fetch_message(int(flags['to']))
            if not react_message:
                # Couldn't find the requested message to react to
                return await ctx.error_reply("Couldn't find that message in this channel!")
        else:
            if flags['up'] and flags['up'].isdigit() and int(flags['up']) < 20:
                distance = int(flags['up']) + 1
            else:
                distance = 2
            # Grab logs
            # TODO: Does this need permission checking?
            logs = ctx.ch.history(limit=distance)
            async for message in logs:
                react_message = message

            # If there wasn't a previous message, whinge
            if react_message is None or react_message == ctx.msg:
                return await ctx.reply("Couldn't find a message to react to!")

        # React to the specified message.
        # Wrap this in try/except in case the message was deleted in the meantime somehow.
        try:
            await ctx.client.http.add_reaction(ctx.ch.id, react_message.id, 
                "{}:{}".format(emoji.name, emoji.id) if emoji_is_custom else emoji['emoji'])
        except discord.NotFound:
            pass
        except discord.HTTPException:
            await ctx.error_reply("I don't have this emoji, so I can't react with it!")

        # If we need to delete the source message, do this now
        if ctx.alias == "sree":
            try:
                await ctx.msg.delete()
            except discord.Forbidden:
                pass

        # Monitor the react message for reactions for a bit. If someone else reacts, remove our reaction.
        try:
            reaction, _ = await ctx.client.wait_for(
                'reaction_add',
                check=lambda reaction, user: (user != ctx.client.user
                                              and reaction.message == react_message
                                              and (reaction.emoji.id == int(emoji.id) if emoji_is_custom else str(reaction) == emoji['emoji'])),
                timeout=60
            )
        except asyncio.TimeoutError:
            pass

        # Remove our reaction (if possible)
        try:
            await react_message.remove_reaction(reaction, ctx.guild.me if ctx.guild else ctx.client.user)
        except Exception:
            pass
    elif enlarged_only:
        # We just want to post an embed with the enlarged emoji as the image.
        embed = discord.Embed(colour=discord.Colour.light_grey())
        await ctx.reply(embed=embed.set_image(url=emoji.url if emoji_is_custom else emoji['url']))
    elif info:
        # We want to post the embed with the enlarged emoji, and as much info as we can get.
        prop_list = []
        value_list = []

        if emoji_is_custom:
            prop_list.append('Name')
            value_list.append(emoji.name)
            prop_list.append('ID')
            value_list.append("`{}`".format(emoji.id))
            prop_list.append('Image link')
            value_list.append('[Click here]({})'.format(emoji.url))
            if emoji.user:
                prop_list.append('Creator')
                value_list.append('{username}#{discriminator}'.format(**emoji.user))
            prop_list.append('Guild')
            value_list.append(emoji.guild)
            created_ago = strfdelta(discord.utils.utcnow() - emoji.created_at)
            created = emoji.created_at.strftime("%I:%M %p, %d/%m/%Y")
            prop_list.append('Created at')
            value_list.append(created)
            prop_list.append('')
            value_list.append(created_ago)
        else:
            prop_list = ['Name', 'Unicode', 'String', 'Image link']
            value_list = [emoji['shortcode'], emoji['unicode'], emoji['emoji'], '[Click here]({})'.format(emoji['url'])]

        desc = prop_tabulate(prop_list, value_list)
        embed = discord.Embed(color=discord.Colour.light_grey(), description=desc, title="Emoji info!")
        embed.set_image(url=emoji.url if emoji_is_custom else emoji['url'])
        await ctx.reply(embed=embed)
    else:
        # Final use case, just post the emoji
        if emoji_is_custom:
            await ctx.reply("<{}:{}:{}>".format('a' if emoji.animated else '', emoji.name, emoji.id))
        else:
            await ctx.reply(emoji['emoji'])
