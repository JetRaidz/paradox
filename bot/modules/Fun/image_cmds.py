import discord
import aiohttp
import urllib
import random

from cmdClient import Context
from utils.ctx_addons import offer_delete

from .module import fun_module as module

# Provides cat, duck, dog, image
"""
Provides some image oriented fun commands

Commands provided:
    cat:
        Sends cat images
    dog:
        Sends dog images
    duck:
        Sends duck images
    holo:
        Sends holo images (and quotes)
    image:
        Searches for an image on Pixabay
"""


@module.cmd("image",
            desc="Searches Pixabay for images matching the specified text.",
            aliases=["imagesearch", "images", "img"])
async def cmd_image(ctx: Context):
    """
    Usage``:
        {prefix}image <image text>
    Description:
        Replies with a random image matching the search description from Pixabay.
    """

    # Pixabay API Key
    # Yeah it shouldn't really be here, but it's a free key with no limitations
    API_KEY = "10259038-12ef42751915ae10017141c86"

    if not ctx.arg_str:
        return await ctx.reply("Please enter something to search for.")
    search_for = urllib.parse.quote_plus(ctx.arg_str)
    async with aiohttp.ClientSession() as sess:
        async with sess.get('https://pixabay.com/api/?key={}&q={}&image_type=photo'.format(API_KEY, search_for)) as r:
            if r.status == 200:
                js = await r.json()
                hits = js['hits'] if 'hits' in js else None
                if not hits:
                    return await ctx.reply("Didn't get any results for this query!")
                hit_pages = []
                for hit in [random.choice(hits) for i in range(20)]:
                    embed = discord.Embed(title="Here you go!", color=discord.Colour.light_grey())
                    if "webformatURL" in hit:
                        embed.set_image(url=hit["webformatURL"])
                    else:
                        continue
                    embed.set_footer(text="Images thanks to the free Pixabay API!")
                    hit_pages.append(embed)
                await ctx.offer_delete(await ctx.pager(hit_pages))
            else:
                return await ctx.error_reply("An error occurred while fetching images. Please try again later.")


@module.cmd("dog",
            desc="Sends a random dog image",
            aliases=["doge", "pupper", "doggo", "woof"])
async def cmd_dog(ctx: Context):
    """
    Usage``:
        {prefix}dog
    Description:
        Replies with a random dog image!
    """
    BASE_URL = "http://random.dog/"
    async with aiohttp.ClientSession() as sess:
        async with sess.get("https://random.dog/woof") as r:
            if r.status == 200:
                dog = await r.text()
                embed = discord.Embed(description="[Woof!]({})".format(BASE_URL + dog), color=discord.Colour.light_grey())
                try:
                    embed.set_image(url=BASE_URL + dog)
                except Exception:
                    return await ctx.error_reply("The file returned was an invalid format. Please try again.")
                else:
                    await ctx.reply(embed=embed)
            else:
                return await ctx.error_reply("An error occurred while fetching dogs. Please try again later.")


@module.cmd("duck",
            desc="Sends a random duck image",
            aliases=["quack"],
            flags=["gif"])
async def cmd_duck(ctx: Context, flags):
    """
    Usage``:
        {prefix}duck [-gif]
    Description:
        Replies with a random duck image!
    Flags::
        gif: Force the response to be in GIF format.
    """
    img_type = "gif" if flags["gif"] else random.choice(["gif", "jpg"])
    async with aiohttp.ClientSession() as sess:
        async with sess.get("http://random-d.uk/api/v1/quack?type={}".format(img_type)) as r:
            if r.status == 200:
                js = await r.json()
                embed = discord.Embed(description="[Quack!]({})".format(js['url']), color=discord.Colour.light_grey())
                embed.set_image(url=js['url'])
                await ctx.reply(embed=embed)
            else:
                return await ctx.error_reply("An error occurred while fetching ducks. Please try again later.")


@module.cmd("cat",
            desc="Sends a random cat image",
            aliases=["meow", "purr", "pussy"],
            flags=["tags==", "caption==", "captioncolour=", "captionsize="])
async def cmd_cat(ctx: Context, flags):
    """
    Usage``:
        {prefix}cat
    Description:
        Replies with a random cat image!
    Flags::
        tags: Search for an image with one of the specified tags.
        caption: Give the result image a caption.
        captioncolour: Change the colour of the caption.
        captionsize: Change the size of the caption.
    """
    BASE_URL = "https://cataas.com/"
    async with aiohttp.ClientSession() as sess:
        if flags["tags"]:
            # Remove any commas beforehand
            flags["tags"] = flags["tags"].replace(",", "")
            # Format the tag arguments as the URL doesn't accept whitespaces between tags.
            tag = "?tags={}".format(",".join(arg for arg in flags["tags"].split()))
            FINAL_URL = BASE_URL + "api/cats" + tag
        else:
            FINAL_URL = BASE_URL + "api/cats"

        if flags["caption"]:
            flags["caption"] = flags["caption"].replace(" ", "%20")
            caption = "/says/" + flags["caption"]
        else:
            caption = False

        if flags["captioncolour"]:
            if flags["captionsize"]:
                colour = "&color={}".format(flags["captioncolour"])
            else:
                colour = "?color={}".format(flags["captioncolour"])
        else:
            colour = False

        if flags["captionsize"]:
            size = "?size={}".format(flags["captionsize"])
        else:
            size = False

        async with sess.get(FINAL_URL) as r:
            if r.status == 200:
                js = await r.json()
                # Get a random cat from the response
                try:
                    cat = random.choice(js)
                except IndexError:
                    # The tag provided wasn't found in any of the available images.
                    return await ctx.error_reply("No images with that tag were found.")
                cid = cat["_id"]
                # If a caption is provided, append it to the URL.
                url = BASE_URL + "cat/{}".format(cid)
                if caption:
                    url += caption

                if size:
                    url += size

                if colour:
                    url += colour

                embed = discord.Embed(description="[Meow!]({})".format(url), color=discord.Colour.light_grey())
                embed.set_image(url=url)
                # If the image has tags, list them in the footer.
                if cat["tags"]:
                    embed.set_footer(text="Tags: {}".format(", ".join(ct for ct in cat["tags"])))
                await ctx.reply(embed=embed)
            else:
                return await ctx.error_reply("An error occurred while fetching cats. Please try again later.")


@module.cmd("holo",
            desc="Holo")
async def cmd_holo(ctx: Context):
    """
    Usage``:
        {prefix}holo
    Image:
        Sends a picture of holo, and a random quote
    """
    async with aiohttp.ClientSession() as sess:
        async with sess.get('http://images.thewisewolf.dev/random') as r:
            if r.status == 200:
                js = await r.json()
                quote = "\"{}\"".format(js["quote"])
                embed = discord.Embed(description=quote, color=discord.Colour.light_grey())
                embed.set_image(url=js['image'])
                await ctx.reply(embed=embed)
            else:
                return await ctx.error_reply("Holo isn't available right now, please come back later")
