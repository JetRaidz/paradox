import discord
import asyncio
import aiohttp
from urllib import parse
import json
from io import BytesIO
from PIL import Image, ImageChops, ImageDraw, ImageFont

from .module import maths_module as module
from .resources import font_path

from utils.lib import emb_add_fields

from . import wolf_data  # noqa
# Provides Wolf

ENDPOINT = "http://api.wolframalpha.com/v2/query?"
WEB = "https://www.wolframalpha.com/"
# WOLF_ICON = "https://content.wolfram.com/uploads/sites/10/2016/12/wa-logo-stacked-small.jpg"
WOLF_ICON = "https://content.wolfram.com/uploads/sites/10/2016/12/wa-logo-stacked-med.jpg"
WOLF_SMALL_ICON = "https://media.discordapp.net/attachments/670154440413675540/703864724122632253/a.png"

# truetype/liberation2/LiberationSans-Bold.ttf
FONT = ImageFont.truetype(font_path, 15, encoding="unic")


def build_web_url(query):
    """
    Returns the url for Wolfram Alpha search for this query.
    """
    return "{}input/?i={}".format(WEB, parse.quote_plus(query))


async def get_query(query, appid, **kwargs):
    """
    Fetches the provided query from the Wolfram Alpha computation engine.
    Has a set of default arguments for the query.
    Any keyword arguments will over-write the defaults.
    Returns the response as a dictionary, or None if the query failed.
    Arguments:
        query: The query to post.
        appid: The Wolfram Appid to use in the query.
        kwargs: Params for the query.
    Returns:
        Dictionary containing results or None if an http error occured.
    """
    # Default params
    payload = {"input": query,
               "appid": appid,
               "format": "image,plaintext",
               "reinterpret": "true",
               "units": "metric",
               "output": "json"}

    # Allow kwargs to overwrite and add to the default params
    payload.update(kwargs)

    # Get the query response
    async with aiohttp.ClientSession() as session:
        async with session.get(ENDPOINT, params=payload) as r:
            if r.status == 200:
                # Read the response, interp as json, and return
                data = await r.read()
                return json.loads(data.decode('utf8'))
            else:
                # If some error occurs, unintelligently fail out
                print(r.status, r)
                return None


async def assemble_pod_image(atoms, dimensions):
    """
    Draws the given atoms onto a canvas of the given dimensions.
    Arguments:
        atoms: A list of dictionaries containing:
            coords, the coordinates to draw the atom.
            text, text to draw at these coords.
            image, the image to paste at these coords.
        dimensions: A tuple (x,y) representing the size of the canvas to draw on.
    Returns:
        An image of the given dimensions with the given atoms drawn on.
    """
    # Make the canvas
    im = Image.new('RGB', dimensions, color=(255, 255, 255))
    draw = ImageDraw.Draw(im)

    # Iterate through the atoms and paste or write each one on as appropriate
    for atom in atoms:
        if "text" in atom:
            draw.text(atom["coord"], atom["text"], fill=(0, 0, 0), font=FONT)
        if "image" in atom:
            im.paste(atom["image"], atom["coord"])
    return im


async def glue_pods(flat_pods):
    """
    Turns a complete list of flattened pods into a list of images, split appropriately.
    Arguments:
        flat_pods: A list of tuples of the form (title, img, level)
    Returns:
        A list of PIL images containing the given pods glued and split as required.
    """
    indent_width = 10
    image_border = 5
    margin = 5

    split_height = 300

    splits = []
    atoms = []
    y_coord = 5
    max_width = 380

    for pod in flat_pods:
        if y_coord > split_height:
            splits.append((atoms, (max_width, y_coord)))
            max_width = 380
            y_coord = 5
            atoms = []

        indent = pod[2] * indent_width
        if pod[0]:
            atoms.append({"coord": (margin + indent, y_coord), "text": pod[0]})
            text_width, text_height = FONT.getsize(pod[0])
            y_coord += text_height
            max_width = max(text_width + indent + 2 * margin, max_width)
        if pod[1]:
            y_coord += image_border
            atoms.append({"coord": (margin + indent + indent_width, y_coord), "image": pod[1]})
            y_coord += pod[1].height
            y_coord += image_border
            max_width = max(pod[1].width + indent + indent_width + image_border + margin, max_width)
    splits.append((atoms, (max_width, y_coord)))
    split_images = []
    for split in splits:
        split_images.append(await assemble_pod_image(*split))
    return split_images


async def flatten_pods(pod_data, level=0, text=False, text_field="plaintext"):
    """
    Takes the list of pods formatted as in wolf ouptut.
    Returns a list of flattened pods as accepted by glue_pods.
    """
    flat_pods = []
    for pod in pod_data:
        if "img" in pod and not text:
            flat_pods.append((pod["title"], await handle_image(pod["img"]), level))
        elif text_field in pod and text:
            flat_pods.append((pod["title"], pod[text_field], level))
        elif "title" in pod:
            flat_pods.append((pod["title"], None, level))
        if "subpods" in pod:
            flat_pods.extend(await flatten_pods(pod["subpods"], level=level + 1, text=text))
    return flat_pods


async def handle_image(image_data):
    """
    Takes an image dict as given by the wolf.
    Retrieves, trims (?) and returns an Image object.
    """
    target = image_data["src"]
    async with aiohttp.ClientSession() as session:
        async with session.get(target, allow_redirects=False) as resp:
            response = await resp.read()
    image = Image.open(BytesIO(response))
    return image
    # return smart_trim(image, border=10)


def smart_trim(im, border=0):
    bg = Image.new(im.mode, im.size, border)
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)


async def pods_to_filedata(pod_data):
    flat_pods = await flatten_pods(pod_data)
    images = await glue_pods(flat_pods)
    output_data = []
    for result in images:
        output = BytesIO()
        result.save(output, format="PNG")
        output.seek(0)
        output_data.append(output)
    return output_data


async def pods_to_textdata(pod_data):
    flat_pods = await flatten_pods(pod_data, text=True)
    tabchar = "​ "
    tab = tabchar * 2

    fields = []
    current_name = ""
    current_lines = []
    for title, text, level in flat_pods:
        if level == 0:
            if current_lines:
                fields.append((current_name if current_name else "Pod", "\n".join(current_lines), 0))
            current_name = title
            current_lines = []
        elif title:
            current_lines.append("{}**{}**".format(tab * level, title))
        if text:
            current_lines.append("{}{}".format(tab * (level + 1), text))
    return fields


def triage_pods(pod_list):
    if "primary" in pod_list[0] and pod_list[0]["primary"]:
        return ([pod_list[0]], pod_list[1:])
    else:
        important = [pod_list[0]]
        important.extend([pod for pod in pod_list if ("primary" in pod and pod["primary"])])
        if len(important) == 1 and len(pod_list) > 1:
            important.append(pod_list[1])
        extra = [pod for pod in pod_list[1:] if pod not in important]
        return (important, extra)


@module.cmd("query",
            desc="Query the [Wolfram Alpha computation engine]({}).".format(WEB),
            flags=["text"],
            aliases=["ask", "wolf", "w", "?w"])
async def cmd_query(ctx, flags):
    """
    Usage``:
        {prefix}ask [query] [--text]
    Description:
        Sends the query to the Wolfram Alpha computational engine and returns the result.
        Use the reactions to show more output or delete the output.
    Flags::
        text: Respond with a copyable text version of the output rather than an image (if possible).
    """
    # Hack to disallow `w` being used with no space
    if ctx.alias == 'w':
        true_args = ctx.msg.content.strip()[len(ctx.prefix):].strip()[1:]
        if not true_args or true_args[0] not in (' ', '\n'):
            return

    # Preload the required emojis
    loading_emoji = ctx.client.conf.emojis.getemoji("loading")
    more_emoji = ctx.client.conf.emojis.getemoji("more")
    prefix = ctx.best_prefix()

    # Handle no arguments
    if not ctx.args:
        return await ctx.error_reply(
            "Please submit a valid query! "
            "For example, `{}ask differentiate x+y^2 with respect to x`.".format(prefix)
        )

    # Send the temporary loading message.
    temp_msg = await ctx.reply("Sending query to Wolfram Alpha, please wait. {}".format(loading_emoji))

    appid = ctx.get_guild_setting.wolfram_id.value if ctx.guild else None
    if appid:
        custom_appid = True
    else:
        custom_appid = False
        appid = ctx.client.conf.get("wolfram_id").strip()

    # Query the API, handle errors
    try:
        result = await get_query(ctx.args, appid)
    except Exception as e:
        return await ctx.error_reply(
            "An unknown exception occurred while fetching the Wolfram Alpha query!\n"
            "If the problem persists please contact support."
        )
    if not result:
        temp_msg = await ctx.safe_delete_msgs(temp_msg)
        return await ctx.error_reply(
            "Failed to get a response from Wolfram Alpha.\n"
            "If the problem persists, please contact support."
        )
    if "queryresult" not in result:
        temp_msg = await ctx.safe_delete_msgs(temp_msg)
        return await ctx.error_reply(
            "Did not get a valid response from Wolfram Alpha.\n"
            "If the problem persists, please contact support."
        )

    link = "[Click here to refine your query online]({})".format(build_web_url(ctx.args))
    link2 = "[Upgrade to WolframAlpha Pro!]({})".format("http://www.wolframalpha.com/pro/")
    if not result["queryresult"]["success"] or result["queryresult"]["numpods"] == 0:
        if result["queryresult"]["error"] and 'code' in result["queryresult"]["error"]:
            error = result["queryresult"]["error"]
            if custom_appid:
                if error['code'] == '1':
                    desc = ("Couldn't send your query!\n"
                            "**Error:** Invalid Wolfram Alpha `AppID`!\n"
                            "Please ask a guild admin to re-configure the `wolfram_id`.\n"
                            "(See `{}config wofram_id` for more information.)").format(ctx.best_prefix())
                else:
                    desc = ("An unknown error occurred querying the WolframAlpha API!\n"
                            "**ERROR:** {}\t{}").format(error['code'], error['msg'])
            else:
                desc = ("There was an unhandled error querying the WolframAlpha API!\n"
                        "This should be fixed soon, but if the issue persists, please contact "
                        "[our support team]({}).").format(ctx.client.app_info["support_guild"])
        else:
            desc = (
                "Wolfram Alpha doesn't understand your query!\n"
                "Perhaps try rephrasing your question?\n{}"
            ).format(link)
        embed = discord.Embed(description=desc)
        embed.set_footer(icon_url=ctx.author.display_avatar, text="Requested by {}".format(ctx.author))
        embed.set_thumbnail(url=WOLF_ICON)
        temp_msg = await ctx.safe_delete_msgs(temp_msg)
        await ctx.offer_delete(await ctx.reply(embed=embed))
        return

    if flags["text"]:
        fields = await pods_to_textdata(result["queryresult"]["pods"])
        embed = discord.Embed(description=link)
        embed.set_footer(icon_url=ctx.author.display_avatar, text="Requested by {}".format(ctx.author))
        embed.set_thumbnail(url=WOLF_ICON)
        emb_add_fields(embed, fields)
        temp_msg = await ctx.safe_delete_msgs(temp_msg)
        out_msg = await ctx.reply(embed=embed)
        out_msg = await ctx.offer_delete(out_msg)
        return

    important, extra = triage_pods(result["queryresult"]["pods"])

    data = (await pods_to_filedata(important))[0]
    output_data = [data]

    embed = discord.Embed(description=link + '\n' + link2)
    embed.set_author(name="Results provided by WolframAlpha",
                     icon_url=WOLF_SMALL_ICON,
                     url="http://www.wolframalpha.com/pro/")
    embed.set_footer(icon_url=ctx.author.display_avatar, text="Requested by {}".format(ctx.author))
    embed.set_thumbnail(url=WOLF_ICON)
    embed.set_image(url="attachment://wolf.png")
    # embed.set_image(url="https://content.wolfram.com/uploads/sites/10/2016/12/WolframAlphaLogo_Web_sanstagline-med.jpg")

    temp_msg = await ctx.safe_delete_msgs(temp_msg)
    dfile = discord.File(data, filename="wolf.png")
    out_msg = await ctx.reply(file=dfile, embed=embed)
    asyncio.ensure_future(ctx.offer_delete(out_msg))

    embed.set_image(url=None)
    if extra:
        try:
            await out_msg.add_reaction(more_emoji)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
        else:
            try:
                reaction, user = await ctx.client.wait_for(
                    'reaction_add',
                    check=lambda reaction, user: (user == ctx.author
                                                  and reaction.message == out_msg
                                                  and reaction.emoji == more_emoji),
                    timeout=300
                )
            except asyncio.TimeoutError:
                try:
                    out_msg = await out_msg.remove_reaction(more_emoji, ctx.me)
                except discord.NotFound:
                    pass
                except Exception:
                    pass
                return
            temp_msg = await ctx.reply("Processing results, please wait. {}".format(loading_emoji))

            output_data[0].seek(0)
            output_data.extend(await pods_to_filedata(extra))
            try:
                await ctx.safe_delete_msgs(temp_msg, out_msg)
            except discord.NotFound:
                pass

            out_msgs = []
            for file_data in output_data[:-1]:
                dfile = discord.File(file_data, filename="wolf.png")
                out_msgs.append(await ctx.reply(file=dfile))
            dfile = discord.File(output_data[-1], filename="wolf.png")
            out_msgs.append(await ctx.reply(file=dfile, embed=embed))
            out_msg = out_msgs[-1]
            asyncio.ensure_future(ctx.offer_delete(out_msg, *out_msgs))

    for output in output_data:
        output.close()
