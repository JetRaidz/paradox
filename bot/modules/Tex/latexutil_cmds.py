from bs4 import BeautifulSoup, NavigableString
import discord
import requests

import urllib.parse
import re

from utils.lib import prop_tabulate

from .module import latex_module as module

"""
Provides ctan and texdoc commands.
"""

texdoc_url = "http://texdoc.net/pkg/{}"
ctan_url = "https://ctan.org/{}"
lion_url = "https://ctan.org/lion/files/ctan_lion_350x350.png"

def soup_site(url: str) -> BeautifulSoup:
    r = requests.get(url)
    return BeautifulSoup(r.text, "html.parser")


line_beginning_re = re.compile(r'^', re.MULTILINE)
whitespace_re = re.compile(r'[\r\n\s\t ]+')


def escape(text):
    if not text:
        return ''
    return text.replace('_', r'\_')


def chomp(text):
    """
    If the text in an inline tag like b, a, or em contains a leading or trailing
    space, strip the string and return a space as suffix of prefix, if needed.
    This function is used to prevent conversions like
        <b> foo</b> => ** foo**
    """
    prefix = ' ' if text and text[0] == ' ' else ''
    suffix = ' ' if text and text[-1] == ' ' else ''
    text = text.strip()
    return (prefix, suffix, text)



class MarkdownConverter(object):

    def __init__(self):
        self.bullets = "-+*"

    def convert(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        return self.process_tag(soup)

    def process_tag(self, node):
        text = ''
        # markdown headings can't include block elements (elements w/newlines)

        # Convert the children first
        for el in node.children:
            if isinstance(el, NavigableString):
                text += self.process_text(str(el))
            else:
                text += self.process_tag(el)

        convert_fn = getattr(self, 'convert_%s' % node.name, None)
        if convert_fn:
            text = convert_fn(node, text)

        return text

    @staticmethod
    def process_text(text):
        return escape(whitespace_re.sub(' ', text or ''))

    @staticmethod
    def indent(text, level):
        return line_beginning_re.sub('\t' * level, text) if text else ''

    @staticmethod
    def underline(text, pad_char):
        text = (text or '').rstrip()
        return '%s\n%s\n\n' % (text, pad_char * len(text)) if text else ''

    def convert_a(self, el, text):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        href = urllib.parse.urljoin(ctan_url, el.get('href'))
        title = el.get('title')
        # For the replacement see #29: text nodes underscores are escaped
        title_part = ' "%s"' % title.replace('"', r'\"') if title else ''
        return '%s[%s](%s%s)%s' % (prefix, text, href, title_part, suffix) if href else text

    def convert_b(self, el, text):
        return self.convert_strong(el, text)

    def convert_span(self, el, text):
        return '%s' % text if text else ''

    def convert_blockquote(self, el, text):
        return '\n' + line_beginning_re.sub('> ', text) if text else ''

    def convert_br(self, el, text):
        return '  \n'

    def convert_em(self, el, text):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        return '%s*%s*%s' % (prefix, text, suffix)

    def convert_i(self, el, text):
        return self.convert_em(el, text)

    def convert_list(self, el, text):

        # Converting a list to inline is undefined.
        # Ignoring convert_to_inline for list.

        nested = False
        while el:
            if el.name == 'li':
                nested = True
                break
            el = el.parent
        if nested:
            # remove trailing newline if nested
            return '\n' + self.indent(text, 1).rstrip()
        return '\n' + text

    convert_ul = convert_list
    convert_ol = convert_list

    def convert_li(self, el, text):
        parent = el.parent
        if parent is not None and parent.name == 'ol':
            if parent.get("start"):
                start = int(parent.get("start"))
            else:
                start = 1
            bullet = '%s.' % (start + parent.index(el))
        else:
            depth = -1
            while el:
                if el.name == 'ul':
                    depth += 1
                el = el.parent
            bullets = self.bullets
            bullet = self.bullets[depth % len(bullets)]
        return '%s %s\n' % (bullet, text or '')

    def convert_p(self, el, text):
        return '%s' % text if text else ''

    def convert_strong(self, el, text):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        return '%s**%s**%s' % (prefix, text, suffix)


def search_n_parse(soup: BeautifulSoup):
    title = soup.find("h1")

    if "Not Found" in title.contents[0]:
        return ("", "", [], [])

    try:
        if "is Gone" in title.contents[2]:
            div = soup.find("div", attrs={"class": "left"})
            desc = div.text
            return (title.text, desc, [], [])
    except IndexError:
        pass

    title = title.text
    converter = MarkdownConverter()
    package_desc = soup.find("p")
    emb_desc = converter.process_tag(package_desc)

    table = soup.find("table")
    prop_list = []
    value_list = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        ignored = ["TDS archive", "Licenses", "Copyright", "Maintainer"]
        if tds[0].text in ignored:
            continue

        brs = tds[1].find_all("br")
        if brs is not None:
            for _ in brs:
                tds[1].br.replace_with(", ")

        links = tds[1].find_all("a")
        if links:
            for link in links:
                if tds[0].text == "Documentation":
                    link.insert_after(", ")
                md_link = "[{}]({})".format(
                    link.text,
                    urllib.parse.urljoin(ctan_url, link.attrs["href"])
                )
                tds[1].a.replace_with(md_link)

        prop_list.append(tds[0].text)
        value_list.append(tds[1].text.rstrip(", "))

    return (title, emb_desc, prop_list, value_list)


@module.cmd("texdoc",
            desc="Searches the [texdoc](http://texdoc.net)",
            aliases=["td"])
async def cmd_texdoc(ctx):
    """
    Usage``:
        {prefix}texdoc <package_name>
    Description:
        Gives a link to the documentation of `package_name` from [texdoc](http://texdoc.net).
        This does not check whether the page exists.
    Examples``:
        {prefix}texdoc tikz
    """
    if len(ctx.args) > 800:
        return await ctx.error_reply("Given query is too long!")
    elif not ctx.args:
        return await ctx.error_reply("Please give me something to search for!")

    await ctx.reply("Documentation for `{}`: {}".format(
        ctx.args,
        texdoc_url.format(urllib.parse.quote_plus(ctx.args))
    ))


@module.cmd("ctan",
            desc="Searches the [ctan](https://ctan.org)",
            aliases=["ctanlink", "ctans"])
async def cmd_ctan(ctx):
    """
    Usage``:
        {prefix}ctan <package_name>
        {prefix}ctans <query>
        {prefix}ctanlink [package_name]
    Description:
        If used as ctan, finds the `package_name` from [ctan](https://ctan.org) and sends the parsed results.

        If used as ctans, searches the ctan, and displays first 10 results.

        If used as ctanlink, provides the direct link to the ctan page with given name of package.
        This does not check whether the page exists.
    Examples``:
        {prefix}ctanlink keyval
        {prefix}ctan amsmath
        {prefix}ctans tables
    """
    url = ctan_url.format("pkg/{}".format(urllib.parse.quote_plus(ctx.args)))
    search_url = ctan_url.format("search?phrase={}&max=10")
    if len(url) > 1500:
        return await ctx.error_reply("Given query is too long!")

    if ctx.alias.lower() == "ctanlink":
        return await ctx.reply(url if ctx.args else ctan_url.format(''))

    if not ctx.args:
        return await ctx.error_reply("Please give me something to search for!")
    # remove special characters but hyphens,underscores,dots from package name
    # special characters make ctan redirect to some non-relevant page
    # e.g `:E` for packages start with an E
    # but we allow hyphens,underscores,dots to be in there because they can be
    # used in a package name
    if not re.sub(r"-|_|\.", "", ctx.args).isalnum():
        return await ctx.error_reply(f"`{ctx.args}` is not a valid package name!")

    loading_emoji = ctx.client.conf.emojis.getemoji("loading")
    out_msg = await ctx.reply("Searching the CTAN, please wait... {}".format(loading_emoji))

    soup = soup_site(url)
    title, desc, prop_list, value_list = search_n_parse(soup)

    if ctx.alias.lower() == "ctans":
        result_url = search_url.format(urllib.parse.quote_plus(ctx.args))
        soup = soup_site(result_url)
        desc = "From {}".format(result_url)
        if title:
            desc += "\nDirect page found at [{args}]({url})".format(args=ctx.args,
                                                                url=url)
        search_title = soup.find("h1").text
        embed = discord.Embed(title=search_title, description=desc)
        stats = soup.find("p").text
        if "no matching" in stats:
            # shows up when you search for unexpected chars, i.e. `[]`
            idx = stats.rfind("You have")
            if idx != -1:
                stats = stats[:idx].strip()

            embed.add_field(name="No results found!", value=stats)
            out_msg = await out_msg.edit(content="", embed=embed)
            return

        urls = soup.find_all("a", attrs={"class": "hit-type-pkg"})
        if not urls:
            embed.add_field(name="No results found!", value="The search found no matching packages on CTAN.")
            out_msg = await out_msg.edit(content="", embed=embed)
            return

        md_links = []
        for url in urls:
            md_link = "[{}]({})".format(
                url.text,
                urllib.parse.urljoin(ctan_url,url.attrs["href"])
            )
            md_links.append(md_link)
        field_value = "\n".join(md_links)
        embed.add_field(name=stats, value=field_value)
        out_msg = await out_msg.edit(content="", embed=embed)
        return

    if not title:
        out_msg = await out_msg.edit(content=f"I couldn't find a package named `{ctx.args}`!")
        return

    if prop_list:
        table = prop_tabulate(prop_list, value_list)
    else:
        table = ""
    read_more = "Read more at [CTAN page]({}) of the package.".format(url)
    if len(desc) > 700:
        desc = desc[:700]
        r_newline = desc.rfind("\n")
        r_space = desc.rfind(" ")
        desc = desc[:r_space if r_space > r_newline else r_newline] + "..."
    if len(table) > 900:
        table = table[:900]
        rightmost_newline = table.rfind("\n")
        table = table[:rightmost_newline+1]
    emb_desc = desc + "\n" + table + read_more
    embed = discord.Embed(
                title=title,
                url=url,
                description=emb_desc,
                color=discord.Color.from_rgb(66, 66, 133)  # ctan's #424285 color
            )
    embed.set_thumbnail(url=lion_url)

    out_msg = await out_msg.edit(content="", embed=embed)
    return
