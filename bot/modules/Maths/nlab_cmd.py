import aiohttp
from bs4 import BeautifulSoup
import urllib
import discord

from utils.lib import emb_add_fields

from .module import maths_module as module

"""
Provides the nlab command
"""


nlab_url = "https://ncatlab.org{}"
search_target = "https://ncatlab.org/nlab/search?query={}"


async def soup_site(target):
    async with aiohttp.ClientSession() as session:
        async with session.get(target, allow_redirects=False) as resp:
            text = await resp.read()
    return BeautifulSoup(text, 'html.parser')


async def search_page_parse(soup):
    in_title = []
    in_body = []
    header_soups = soup.find_all("h2")
    if "No pages contain" in header_soups[0].contents[0]:
        return ([], [])
    if len(header_soups) > 2:
        return None
    elif len(header_soups) == 2:
        in_title = results_parse(header_soups[0])
        in_body = results_parse(header_soups[1])
    elif len(header_soups) == 0:
        return ([], [])
    else:
        in_title = []
        in_body = results_parse(header_soups[0])
    return (in_title, in_body)


def results_parse(soup):
    links = soup.nextSibling.nextSibling.findAll("a")
    results = ((a.contents[0], a.attrs["href"]) for a in links)
    return results


async def search_for(string):
    soup = await soup_site(search_target.format(urllib.parse.quote_plus(string)))
    if "Search results" not in soup.find("title").contents:
        return None
    return await search_page_parse(soup)


def field_pager(strings):
    pages = []
    this_page = []
    this_length = 0

    for string in strings:
        this_length += len(string) + 1
        if this_length > 1000:
            pages.append("\n".join(this_page))
            this_page = []
            this_length = len(string) + 1

        this_page.append(string)

    if this_page:
        pages.append("\n".join(this_page))

    return pages


@module.cmd("nlab",
            desc="Searches the [nlab](https://ncatlab.org)",
            aliases=["nlablink", "nl"])
async def cmd_nlab(ctx):
    """
    Usage``:
        {prefix}nlab <search>
        {prefix}nlablink <page name>
    Description:
        If used as nlab, searches the [nlab](https://ncatlab.org) for the `search` string.

        If used as nlablink, provides the direct link to the nlab page with the given name.
        This does not check whether the page exists.
    Examples``:
        {prefix}nlablink category
        {prefix}nlab categorical group
    """
    direct_page = nlab_url.format("/nlab/show/{}".format(urllib.parse.quote_plus(ctx.args)))
    if len(direct_page) > 1500:
        return await ctx.error_reply("Search string given is too long!")

    if ctx.alias.lower() == "nlablink":
        await ctx.reply(direct_page if ctx.args else nlab_url[:-2])
        return

    if not ctx.args:
        return await ctx.error_reply("Please give me something to search for!")

    loading_emoji = ctx.client.conf.emojis.getemoji('loading')

    out_msg = await ctx.reply("Searching the ncatlab, please wait. {}".format(loading_emoji))

    url = search_target.format(urllib.parse.quote_plus(ctx.args))

    soup = await soup_site(url)
    direct_soup = await soup_site(direct_page)
    direct_found = False if (
        not direct_soup.find("title") or "Page not found" in direct_soup.find("title").contents[0]
    ) else True
    direct_str = "\nDirect page found at: [{}]({})".format(ctx.args, direct_page) if direct_found else ""

    title = soup.find("title")
    if title is None or "Search results" not in title.contents[0]:
        out_msg = await out_msg.edit(
            content="Nlab redirected the search to the following page:\n{}".format(soup.find("a").attrs["href"])
        )
        return
    parsed = await search_page_parse(soup)
    if not parsed:
        out_msg = await out_msg.edit(
            content="I don't understand the search results. Read them yourself at:\n{}".format(url)
        )
        return
    in_title, in_body = parsed

    in_title_fields = []
    if in_title:
        in_title = list(in_title)
        in_title_links = ["[{}]({})".format(link[0], nlab_url.format(link[1])) for link in in_title]
        in_title_fields_raw = field_pager(in_title_links)

        base_title = "{} result{} where query appeared in title.".format(
            len(in_title), "" if len(in_title) == 1 else "s"
        )
        if len(in_title_fields_raw) == 1:
            in_title_fields = [(base_title, in_title_fields_raw[0], 0)]
        else:
            page_num = len(in_title_fields_raw)
            in_title_fields = [
                ("{} (Page {}/{})".format(base_title, i + 1, page_num), page, 0)
                for i, page in enumerate(in_title_fields_raw)
            ]

    in_body_fields = []
    if in_body:
        in_body = list(in_body)
        in_body_links = ["[{}]({})".format(link[0], nlab_url.format(link[1])) for link in in_body]
        in_body_fields_raw = field_pager(in_body_links)

        base_title = "{} result{} where query appeared in body.".format(len(in_body), "" if len(in_body) == 1 else "s")
        if len(in_body_fields_raw) == 1:
            in_body_fields = [(base_title, in_body_fields_raw[0], 0)]
        else:
            page_num = len(in_body_fields_raw)
            in_body_fields = [
                ("{} (Page {}/{})".format(base_title, i + 1, page_num), page, 0)
                for i, page in enumerate(in_body_fields_raw)
            ]

    if not in_title and not in_body:
        out_msg = await out_msg.edit(content="No results found at:\n{}".format(url))
        return

    emb_pages = []
    emb_pages.extend([[field] for field in in_title_fields[:-1]])

    middle_page = []
    if in_title_fields:
        middle_page.append(in_title_fields[-1])
    if in_body_fields:
        middle_page.append(in_body_fields[0])
    if middle_page:
        emb_pages.append(middle_page)

    emb_pages.extend([[field] for field in in_body_fields[1:]])

    params = {"title": "Search results for {}".format(ctx.args),
              "description": "From {}{}".format(url, direct_str),
              "color": discord.Colour.light_grey()
              }

    embeds = []
    for page in emb_pages:
        page_embed = discord.Embed(**params)
        emb_add_fields(page_embed, page)
        embeds.append(page_embed)

    try:
        await out_msg.delete()
    except discord.NotFound:
        pass
    await ctx.pager(embeds)
