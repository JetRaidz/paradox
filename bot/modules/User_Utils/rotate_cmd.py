import asyncio
import mimetypes as mtypes
from io import BytesIO

import aiohttp
from PIL import Image
import discord

from .module import utils_module as module

# Provides rotate


@module.cmd("rotate",
            desc="Rotates the last image.",
            aliases=['rcw', 'rccw'])
async def cmd_rotate(ctx):
    """
    Usage``:
        {prefix}rotate [amount]
        {prefix}rcw [amount]
        {prefix}rccw [amount]
    Description:
        Rotates the last image (within the last `10` messages) by `amount` degrees, or `90` if not specified.
        If an image is attached, the attachment will be used instead.
    Aliases::
        rcw: Rotate clockwise.
        rccw: Rotate counterclockwise.
        rotate: If `amount` is given, rotate clockwise, otherwise rotate counterclockwise.
    """

    amount = -1 * int(ctx.args) if (ctx.args
                                    and (ctx.args.isdigit()
                                         or (len(ctx.args) > 1
                                             and ctx.args[0] == '-'
                                             and ctx.args[1:].isdigit()))) else None

    amount = -1 * amount if amount is not None and ctx.alias == "rccw" else amount
    amount = amount if amount is not None else (90 if ctx.alias != "rcw" else -90)

    if ctx.guild and not ctx.ch.permissions_for(ctx.guild.me).read_message_history:
        return await ctx.error_reply("I need the `Read Message History` permission in this channel to do this!")

    image_url = None
    async for message in ctx.ch.history(limit=10):
        # Check for image uploaded with message
        if (
            message.attachments and
            message.attachments[-1].height and
            message.attachments[-1].filename and
            (mtypes.guess_type(message.attachments[-1].filename)[0] or "").startswith('image')
        ):
            image_url = message.attachments[-1].proxy_url
            break

        for embed in reversed(message.embeds):
            if embed.type == 'image':
                # Image embedded from a url in content
                image_url = message.embeds[0].url
                break
            elif embed.type == 'rich':
                # Image set in a rich embed
                if embed.image:
                    image_url = embed.image.proxy_url
                    break

        if image_url is not None:
            break

    if image_url is None:
        return await ctx.error_reply("Couldn't find an attached image in the last 10 messages.")

    if ctx.msg.attachments:
        if (
            ctx.msg.attachments[0].height and 
            ctx.msg.attachments[0].filename and 
            (mtypes.guess_type(ctx.msg.attachments[0].filename)[0] or "").startswith('image')
        ):
            image_url = ctx.msg.attachments[0].proxy_url

    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as r:
            if r.status == 200:
                response = await r.read()
            else:
                return await ctx.error_reply("Retrieving the previous image failed.")

    with Image.open(BytesIO(response)) as im:
        await _rotate(ctx, im, amount, ctx.author.id)

emoji_rotate_cw = "↩️"
emoji_rotate_ccw = "↪️"


async def _rotate(ctx, im, amount, name):
    # Rotate and crop the image
    exif = im.info.get('exif', None)
    rotated = im.rotate(amount, expand=1)
    bbox = rotated.getbbox()
    rotated = rotated.crop(bbox)

    with BytesIO() as output:
        if exif:
            rotated.convert("RGB").save(output, exif=exif, format="JPEG", quality=85, optimize=True)
        else:
            rotated.convert("RGB").save(output, format="JPEG", quality=85, optimize=True)
        output.seek(0)
        dfile = discord.File(output, filename="{}.png".format(name))
        out_msg = await ctx.reply(file=dfile)
        if out_msg:
            try:
                asyncio.ensure_future(ctx.offer_delete(out_msg))
                await out_msg.add_reaction(emoji_rotate_ccw)
                await out_msg.add_reaction(emoji_rotate_cw)
            except discord.Forbidden:
                return
            except discord.NotFound:
                return

            while True:
                try:
                    reaction, user = await ctx.client.wait_for(
                        'reaction_add',
                        check=lambda r, u: (
                            r.message == out_msg
                            and u == ctx.author
                            and r.emoji in (emoji_rotate_cw, emoji_rotate_ccw)
                        ),
                        timeout=300
                    )
                except asyncio.TimeoutError:
                    try:
                        me = ctx.guild.me if ctx.guild else ctx.client.user
                        if out_msg:
                            await out_msg.remove_reaction(emoji_rotate_cw, me)
                            await out_msg.remove_reaction(emoji_rotate_ccw, me)
                    except discord.NotFound:
                        pass
                    except discord.HTTPException:
                        pass
                    return
                try:
                    out_msg = await out_msg.delete()
                except discord.NotFound:
                    return

                await _rotate(ctx, im, amount + (90 if reaction.emoji == emoji_rotate_ccw else -90), name)
