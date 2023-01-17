import discord
import requests
from cmdClient import Context
from utils.interactive import pager
from utils.lib import paginate_list

from .module import fun_module as module

"""
Some simple fun utility commands.

Commands provided:
    convertbinary:
        Translates a binary string to ascii
    lenny:
        Sends a lenny face
    sorry:
        Sends a sorry image
    discrim:
        Sends a list of users with matching discriminator
"""


@module.cmd("convertbinary", 
            desc="Converts binary to text.", 
            aliases=["bin2t", "binarytotext", "convbin"])
async def cmd_convertbinary(ctx: Context):
    """
    Usage``:
        {prefix}convertbinary <binary string>
    Description:
        Converts the provided binary string into text.
    """
    bitstr = ctx.arg_str.replace(' ', '')
    if (not bitstr.isdigit()) or (len(bitstr) % 8 != 0):
        await ctx.reply("Please provide a valid binary string!")
        return
    bytelist = map(''.join, zip(*[iter(bitstr)] * 8))
    asciilist = [chr(sum([int(b) << 7 - n for (n, b) in enumerate(byte)])) for byte in bytelist]
    await ctx.reply("Output: `{}`".format(''.join(asciilist)))


@module.cmd("lenny",
            desc="( ͡° ͜ʖ ͡°)")
async def cmd_lenny(ctx: Context):
    """
    Usage``:
        {prefix}lenny
    Description:
        Sends lenny ( ͡° ͜ʖ ͡°).
    """
    try:
        await ctx.msg.delete()
    except discord.Forbidden:
        pass
    await ctx.reply("( ͡° ͜ʖ ͡°)")


@module.cmd("sorry",
            desc="Sorry, love.")
async def cmd_sorry(ctx: Context):
    """
    Usage``:
        {prefix}sorry
    Description:
        Sorry, love.
    """
    try:
        embed = discord.Embed(color=discord.Colour.purple())
        embed.set_image(url="https://cdn.discordapp.com/attachments/309625872665542658/406040395462737921/image.png")
        await ctx.reply(embed=embed)
    except discord.Forbidden:
        return await ctx.error_reply("I don't have permission to send embeds here!")
    except Exception:
        pass
