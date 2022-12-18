from datetime import datetime
import string

import discord
import aiohttp

# from pytz import timezone

from utils import seekers  # noqa
from utils.lib import split_text, prop_tabulate

from wards import in_guild, chunk_guild

from .module import utils_module as module
from resources.colours import XTERM256_COLOURS


@module.cmd("echo",
            desc="Sends what you tell me to!")
async def cmd_echo(ctx):
    """
    Usage``:
        {prefix}echo <text>
    Description:
        Replies to the message with `text`.

        (Note: This command may be disabled with `{prefix}disablecmd echo`.)
    """
    await ctx.reply(
        discord.utils.escape_mentions(ctx.args)
        if ctx.args
        else "I can't send an empty message!"
    )


@module.cmd("secho",
            desc="Deletes your message and echos it.")
async def cmd_secho(ctx):
    """
    Usage``:
        {prefix}secho <text>
    Description:
        Replies to the message with `text` and deletes your message.

        (Note: This command may be disabled with `{prefix}disablecmd secho`.)
    """
    try:
        if ctx.args:
            await ctx.msg.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass

    await ctx.reply(
        discord.utils.escape_mentions(ctx.args)
        if ctx.args
        else "I can't send an empty message!"
    )


@module.cmd("jumpto",
            desc="Finds the given message ID and generates a jump link.")
@in_guild()
async def cmd_jumpto(ctx):
    """
    Usage``:
        {prefix}jumpto <msgid>
    Description:
        Searches for the given `msgid` amongst all the guild channels you can see, then replies with the jump link.
    Examples``:
        {prefix}jumpto {ctx.msg.id}
    """
    error_msg = "Please provide a valid message ID."
    if not ctx.args:
        return await ctx.error_reply(error_msg)
    msgid = ctx.args.split()[0]
    if not msgid.isdigit():
        return await ctx.error_reply(error_msg)
    msgid = int(msgid)

    # Placeholder output
    embed = discord.Embed(
        colour=discord.Colour.green(),
        description="Searching for message {}".format(
            ctx.client.conf.emojis.getemoji("loading")
        ),
    )
    out_msg = await ctx.reply(embed=embed)

    # Try looking in the current channel first
    message = None
    try:
        message = await ctx.ch.fetch_message(msgid)
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass

    if message is None:
        # A more thorough seek is required
        message = await ctx.find_message(msgid, ignore=[ctx.ch.id])

    if message is None:
        embed.description = "Couldn't find the message!"
        embed.colour = discord.Colour.red()
    else:
        embed.description = "[Jump to message]({})".format(message.jump_url)

    try:
        out_msg = await out_msg.edit(embed=embed)
    except discord.NotFound:
        await ctx.reply(embed=embed)


@module.cmd("quote",
            desc="Quotes a message by ID.",
            flags=["a", "r"])
@in_guild()
async def cmd_quote(ctx, flags):
    """
    Usage``:
        {prefix}quote <messageid> [-a] [-r]
    Description:
        Searches for the given `messageid` amongst messages in channels (of the current guild) that you can see, \
            and replies with the desired message in an embed.
    Flags::
        -a: (anonymous) Removes author information from the quote.
        -r: (raw) Put the message content in a codeblock.
    Examples``:
        {prefix}quote {ctx.msg.id}
    """
    error_msg = "Please provide a valid message ID."
    if not ctx.args:
        return await ctx.error_reply(error_msg)
    msgid = ctx.args.split()[0]
    if not msgid.isdigit():
        return await ctx.error_reply(error_msg)
    msgid = int(msgid)

    # Placeholder output
    embed = discord.Embed(
        colour=discord.Colour.green(),
        description="Searching for message {}".format(
            ctx.client.conf.emojis.getemoji("loading")
        ),
    )
    out_msg = await ctx.reply(embed=embed)

    # Try looking in the current channel first
    message = None
    try:
        message = await ctx.ch.fetch_message(msgid)
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass

    if message is None:
        # A more thorough seek is required
        message = await ctx.find_message(msgid, ignore=[ctx.ch.id])

    if message is None:
        embed.description = "Couldn't find the message!"
        embed.colour = discord.Colour.red()
        try:
            out_msg = await out_msg.edit(embed=embed)
        except discord.NotFound:
            await ctx.reply(embed=embed)
    else:
        quote_content = (
            message.content.replace("```", "[CODEBLOCK]")
            if flags["r"]
            else message.content
        )

        header = "[Click to jump to message]({})".format(message.jump_url)
        blocks = split_text(quote_content, 1000, code=flags["r"])

        embeds = []
        for block in blocks:
            desc = header + "\n" + block
            embed = discord.Embed(
                colour=discord.Colour.light_grey(),
                description=desc,
                timestamp=message.created_at,
            )

            if not flags["a"]:
                embed.set_author(
                    name="{user.name}".format(user=message.author),
                    icon_url=message.author.avatar.url,
                )
            embed.set_footer(text="Sent in #{}".format(message.channel.name))
            if message.attachments:
                embed.set_image(url=message.attachments[0].proxy_url)
            embeds.append(embed)

        try:
            if len(embeds) == 1:
                out_msg = await out_msg.edit(embed=embeds[0])
            else:
                out_msg = await out_msg.delete()
                await ctx.pager(embeds, locked=False)
        except discord.NotFound:
            await ctx.pager(embeds, locked=False)


@module.cmd("invitebot",
            desc="Generates a bot invite link for a given bot or botid.",
            aliases=["ibot"])
@chunk_guild()
async def cmd_invitebot(ctx):
    """
    Usage``:
        {prefix}invitebot <bot>
    Description:
        Replies with an invite link for the bot.
        `bot` must be an id or a partial name or mention.
    Examples``:
        {prefix}invitebot {ctx.author.display_name}
    """
    user = None
    userid = None

    if ctx.args.isdigit():
        userid = int(ctx.args)
    elif ctx.guild:
        user = await ctx.find_member(ctx.args, interactive=True)
        if not user:
            return
        userid = user.id
    else:
        return ctx.error_reply(
            "Please supply a bot client id to get the invite link for."
        )

    invite_link = "<https://discordapp.com/api/oauth2/authorize?client_id={}&permissions=0&scope=bot>".format(
        userid
    )

    if userid == ctx.author.id:
        await ctx.reply("Hey, do you want to come hang out?")
    elif userid == ctx.client.user.id:
        await ctx.reply(
            "Sure, I would love to!\n"
            "My official invite link is: {}\n"
            "If you don't want to invite me with my usual permissions, you can also use:\n"
            "{}".format(ctx.client.app_info["invite_link"], invite_link)
        )
    elif user is not None and not user.bot:
        await ctx.reply("Maybe you could try asking them nicely?")
    else:
        await ctx.reply(
            "Permissionless invitelink for `{}`:\n" "{}".format(userid, invite_link)
        )


@module.cmd("piggybank",
            desc="Keep track of money added towards a goal.",
            aliases=["bank"],
            disabled=True)
async def cmd_piggybank(ctx):
    """
    Sorry!:
        Feature temporarily disabled pending the next update.
    """
    """
    Usage:
        {prefix}piggybank [+|- <amount>] | [list [clear]] | [goal <amount>|none]
    Description:
        [+|- <amount>]: Adds or removes an amount to your piggybank.
        [list [clear]]: Sends you a DM with your previous transactions or clears your history.
        [goal <amount>|none]: Sets your goal!
        Or with no arguments, lists your current amount and progress to the goal.
    """
    await ctx.reply(
        embed=discord.Embed(
            title="Sorry!",
            description="`piggybank` has been temporarily disabled pending the next update.",
        )
    )


#     bank_amount = await ctx.data.users.get(ctx.authid, "piggybank_amount")
#     transactions = await ctx.data.users_long.get(ctx.authid, "piggybank_history")
#     goal = await ctx.data.users.get(ctx.authid, "piggybank_goal")
#     bank_amount = bank_amount if bank_amount else 0
#     transactions = transactions if transactions else {}
#     goal = goal if goal else 0
#     if ctx.arg_str == "":
#         msg = "You have ${:.2f} in your piggybank!".format(bank_amount)
#         if goal:
#             msg += "\nYou have achieved {:.1%} of your goal (${:.2f})".format(bank_amount / goal, goal)
#         await ctx.reply(msg)
#         return
#     elif (ctx.params[0] in ["+", "-"]) and len(ctx.params) == 2:
#         action = ctx.params[0]
#         now = datetime.utcnow().strftime('%s')
#         try:
#             amount = float(ctx.params[1].strip("$#"))
#         except ValueError:
#             await ctx.reply("The amount must be a number!")
#             return
#         transactions[now] = {}
#         transactions[now]["amount"] = "{}${:.2f}".format(action, amount)
#         bank_amount += amount if action == "+" else -amount
#         await ctx.data.users.set(ctx.authid, "piggybank_amount", bank_amount)
#         await ctx.data.users_long.set(ctx.authid, "piggybank_history", transactions)
#         msg = "${:.2f} has been {} your piggybank. You now have ${:.2f}!".format(amount,
#                                                                                  "added to" if action == "+" else "removed from",
#                                                                                  bank_amount)
#         if goal:
#             if bank_amount >= goal:
#                 msg += "\nYou have achieved your goal!"
#             else:
#                 msg += "\nYou have now achieved {:.1%} of your goal (${:.2f}).".format(bank_amount / goal, goal)
#         await ctx.reply(msg)
#     elif (ctx.params[0] == "goal") and len(ctx.params) == 2:
#         if ctx.params[1].lower() in ["none", "remove", "clear"]:
#             await ctx.data.users.set(ctx.authid, "piggybank_goal", amount)
#             await ctx.reply("Your goal has been cleared")
#             return
#         try:
#             amount = float(ctx.params[1].strip("$#"))
#         except ValueError:
#             await ctx.reply("The amount must be a number!")
#             return
#         await ctx.data.users.set(ctx.authid, "piggybank_goal", amount)
#         await ctx.reply("Your goal has been set to ${}. ".format(amount))
#     elif (ctx.params[0] == "list"):
#         if len(transactions) == 0:
#             await ctx.reply("No transactions to show! Start adding money to your piggy bank with `{}piggybank + <amount>`".format(ctx.used_prefix))
#             return
#         if (len(ctx.params) == 2) and (ctx.params[1] == "clear"):
#             await ctx.data.users_long.set(ctx.authid, "piggybank_history", {})
#             await ctx.reply("Your transaction history has been cleared!")
#             return

#         msg = "```\n"
#         for trans in sorted(transactions):
#             trans_time = datetime.utcfromtimestamp(int(trans))
#             tz = await ctx.data.users.get(ctx.authid, "tz")
#             if tz:
#                 try:
#                     TZ = timezone(tz)
#                 except Exception:
#                     pass
#             else:
#                 TZ = timezone("UTC")
#             timestr = '%I:%M %p, %d/%m/%Y (%Z)'
#             timestr = TZ.localize(trans_time).strftime(timestr)
#             msg += "{}\t {:^10}\n".format(timestr, str(transactions[trans]["amount"]))
#         await ctx.reply(msg + "```", dm=True)
#     else:
#         await ctx.reply("Usage: {}piggybank [+|- <amount>] | [list] | [goal <amount>|none]".format(ctx.used_prefix))


def nearest_xterm256(colour: str) -> tuple[int, str]:
    """Returns the nearest xterm256 colour to the given colour."""
    return min(
        XTERM256_COLOURS.items(),
        key=lambda x: sum(
            (int(x[1][i + 1: i + 3], 16) - int(colour[i: i + 2], 16)) ** 2
            for i in range(0, 6, 2)
        ),
    )


@module.cmd("colour",
            desc="Displays information about a colour.",
            aliases=["color"],
            flags=["hex", "rgb", "xterm"])
async def cmd_colour(ctx, flags):
    """
    Usage``:
        {prefix}colour <value>
    Description:
        Displays some detailed information about the colour.
    Flags::
        hex: Treat the value as a 3 or 6-digit hex value. (default)
        rgb: Treat the value as an RGB value.
        xterm: Treat the value as an xterm-256 colour.
    Examples``:
        {prefix}colour #0047AB
        {prefix}colour #04A
        {prefix}colour --rgb 0 17 135
        {prefix}colour --xterm 73
    """
    # TODO: Support for names
    # Parse flag arguments
    if any(flags.values()):
        # ensure only one flag is set
        if sum(flags.values()) > 1:
            return await ctx.error_reply("Please only use one flag at a time.")
    # if no flags are set, assume hex
    else:
        flags["hex"] = True

    # Parse colour argument for hex
    if flags["hex"]:
        stripped: str = ctx.args.strip("#")
        if len(stripped) not in (3, 6) or not all(
            c in string.hexdigits for c in stripped
        ):
            return await ctx.error_reply(
                "Please give me a valid hex colour (e.g. #0047AB, 0047AB, #8ad, 7AB)"
            )
        elif len(stripped) == 3:
            hexstr = "".join(c * 2 for c in stripped)
        elif len(stripped) == 6:
            hexstr = stripped

    # Parse colour argument for rgb
    elif flags["rgb"]:
        RGB_ERRMSG: str = "Please provide a valid combination of RGB values (between 0 and 255) e.g. 0,71,171 or 0 71 171"
        # exit out if there are no args
        if not ctx.args:
            return await ctx.error_reply(f"{RGB_ERRMSG}")
        else:
            rgb_parsed: bool = False
            rgb_splits: list[str] = (
                ctx.args.split(",") if "," in ctx.args else ctx.args.split()
            )
            rgb_splits: list[str] = [split.strip() for split in rgb_splits]

            if len(rgb_splits) == 3 and all(split.isdigit() for split in rgb_splits):
                rgb_values = tuple(map(int, rgb_splits))
                if all(0 <= value <= 255 for value in rgb_values):
                    rgb_parsed = True
                    hexstr = "".join(f"{value:02x}" for value in rgb_values)

            if not rgb_parsed:
                return await ctx.error_reply(f"{RGB_ERRMSG}")

    # Parse colour argument for xterm256
    elif flags["xterm"]:
        XTERM_ERRMSG: str = "Please provide a valid xterm256 colour (between 0 and 255)"
        if not ctx.args.isdigit() or not 0 <= (xterm := int(ctx.args)) <= 255:
            return await ctx.error_reply(f"{XTERM_ERRMSG}")
        hexstr: str = XTERM256_COLOURS[xterm].strip("#")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://www.thecolorapi.com/id?hex={hexstr}") as r:
            if r.status == 200:
                js = await r.json()
                inverted = col_invert(hexstr)
                prop_list = ["rgb", "hsl", "hsv", "cmyk", "XYZ"]
                value_list = [js[prop]["value"][len(prop) :] for prop in prop_list]
                desc = prop_tabulate(prop_list, value_list)
                embed = discord.Embed(
                    title=f"Colour info for `#{hexstr}`",
                    color=discord.Colour(int(hexstr, 16)),
                    description=desc,
                )
                # format the colour values with 3 spaces and fill with spaces
                embed.add_field(
                    name="Closest named colour",
                    value=f'`{js["name"]["value"]}` (Hex `{js["name"]["closest_named_hex"]:<3}`)',
                )
                # show closest xterm256 colour unless the flag was xterm
                if not flags["xterm"]:
                    nearest_xterm_colour, nearest_xterm_hex = nearest_xterm256(hexstr)
                    embed.add_field(
                        name="Closest xterm256 colour",
                        value=f'`{nearest_xterm_colour}` (Hex `{nearest_xterm_hex}`)',
                        inline=False
                    )
                # add a thumbnail with the colour
                embed.set_thumbnail(
                    url=f"https://dummyimage.com/100x100/{hexstr}/{inverted}.png&text={hexstr}"
                )
                await ctx.reply(embed=embed)
            else:
                return await ctx.error_reply(
                    "Sorry, something went wrong while fetching your colour! Please try again later"
                )


def col_invert(color_to_convert):
    table = str.maketrans("0123456789abcdef", "fedcba9876543210")
    return color_to_convert.lower().translate(table).upper()
