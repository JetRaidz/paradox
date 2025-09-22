import os
import re
import time
import logging
import asyncio
import discord

from logger import log

from cmdClient import cmdClient, Context

from ..module import latex_module as module

from .tex_utils import ParseMode, TexNameStyle
from ..resources import default_preamble, failed_image_path
from .LatexUser import LatexUser
from .LatexGuild import LatexGuild
from .tex_compile import makeTeX  # noqa


class BucketFull(Exception):
    """
    Throw when a requested Bucket is already full
    """
    pass


class BucketOverFull(BucketFull):
    """
    Throw when a requested Bucket is overfull
    """
    pass


class Bucket:
    __slots__ = ('max_level', 'empty_time', 'leak_rate', '_level', '_last_checked', '_last_full')

    def __init__(self, max_level, empty_time):
        self.max_level = max_level
        self.empty_time = empty_time
        self.leak_rate = max_level / empty_time

        self._level = 0
        self._last_checked = time.time()

        self._last_full = False

    @property
    def overfull(self):
        self._leak()
        return self._level > self.max_level

    def _leak(self):
        if self._level:
            elapsed = time.time() - self._last_checked
            self._level = max(0, self._level - (elapsed * self.leak_rate))

        self._last_checked = time.time()

    def request(self):
        self._leak()
        if self._level + 1 > self.max_level + 1:
            raise BucketOverFull
        elif self._level + 1 > self.max_level:
            self._level += 1
            if self._last_full:
                raise BucketOverFull
            else:
                self._last_full = True
                raise BucketFull
        else:
            self._last_full = False
            self._level += 1


class LatexContext:
    __slots__ = (
        'ctx', 'source', 'lguild', 'luser',
        '_force_wide', 'wide', 'keepsourcefor', 'preamble', '_errors',
        '_source_message', '_dm_source', '_header_name', '_spoiler_output',
        '_output_message', '_source_shown', '_header_collapsed', '_header_shown',
        '_show_emoji', '_source_deletion_task', '_lifetime_task', '_last_reaction'
    )

    # Compiled regex for the `$` latex content checker
    single_dollars_pattern = re.compile(r"\$(?=\S)[^$]+(?<=\S)\$")
    double_dollars_pattern = re.compile(r"\$\$[^$]+\$\$")

    # Locks to avoid simultaneous compilation for each user
    user_locks = {}  # userid: Lock

    # Buckets to ratelimit latex requests
    user_buckets = {}  # userid: Bucket

    # Collection of LatexContexts listening for reactions by output message id
    active_contexts = {}

    # Time to stay active for, after the last reaction
    active_lifetime = 300

    # Emojis, populated on initialisation
    emoji_delete = None
    emoji_show_source = None
    emoji_show_errors = None
    emoji_delete_source = None

    def __init__(self, ctx: Context, source, lguild=None, luser=None, wide=None, spoiler=False):
        self.ctx = ctx
        self.source = source
        self.lguild = lguild or LatexGuild.get(ctx.guild.id if ctx.guild else 0)
        self.luser = luser or LatexUser.get(ctx.author.id)

        # One-time forced compile flags
        self._force_wide = wide

        # Cached configuration properties, loaded from user and guild
        self.wide = self.get_wide()
        self.keepsourcefor = self.get_keepsourcefor()
        self.preamble = self.get_preamble()

        # Pre-compile parameters
        self._source_message = ctx.msg
        self._dm_source = len(source) > 1000
        self._header_name = self.get_header_name()
        self._spoiler_output = spoiler

        # Running latex state
        self._errors = None
        self._output_message = None
        self._source_shown = False
        self._header_collapsed = None
        self._header_shown = None
        self._show_emoji = None
        self._source_deletion_task = None
        self._lifetime_task = None
        self._last_reaction = None

    # Compute configuration in current context from user, guild, and defaults
    def get_preamble(self):
        """
        Retrieve the current compilation preamble.
        """
        return self.luser.preamble or self.lguild.preamble or default_preamble

    def get_wide(self):
        return self._force_wide if self._force_wide is not None else self.luser.alwayswide

    def get_keepsourcefor(self):
        return self.luser.keepsourcefor

    def get_header_name(self):
        if self.luser.namestyle == TexNameStyle.HIDDEN:
            name = ""
        elif self.luser.namestyle == TexNameStyle.MENTION:
            name = "<@{}>\n".format(self.luser.id)
        else:
            if self.luser.namestyle == TexNameStyle.DISPLAYNAME:
                raw_name = self.ctx.author.display_name
            elif self.luser.namestyle == TexNameStyle.USERNAME:
                raw_name = self.ctx.author.name
            else:
                raise ValueError("Unknown LatexUser namestyle `{}`.".format(self.luser.namestyle))

            name = "{}\n".format(
                discord.utils.escape_mentions(discord.utils.escape_markdown(raw_name))
            )
        return name

    def get_header(self):
        return self._header_shown if self._source_shown else self._header_collapsed

    async def dm_source(self, target):
        embed = discord.Embed(title="LaTeX source",
                              description="```latex\n{}\n```".format(self.source),
                              timestamp=self._source_message.created_at)
        embed.set_footer(text="Sent at")
        embed.set_author(name=self._header_name)

        if self._errors:
            embed.add_field(
                name="Compile Errors",
                value="```{}```".format(self._errors.replace("```", "")),
                inline=False
            )

        embed.add_field(
            name="Jump link",
            value="[Click here to jump back to the message]({})".format(self._output_message.jump_url),
            inline=False
        )
        try:
            await target.send(embed=embed)
        except discord.Forbidden:
            await self.ctx.error_reply(
                "Could not direct message you {}, "
                "do you have me blocked or direct messages disabled?".format(target.mention)
            )

    async def delete_source(self, delay=0):
        """
        Delete the source message, possibly after the configured delay.
        Don't run the deletion if the message was edited since we started.
        """
        try:
            if self._source_message:
                if delay:
                    # Wait for the delay, and abort if the message has been edited while we wait
                    last_modified = self._source_message.edited_at or self._source_message.created_at
                    await asyncio.sleep(delay)
                    if self._source_message.edited_at and last_modified < self._source_message.edited_at:
                        return
                await self._source_message.delete()
        except asyncio.CancelledError:
            pass
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass

    async def lifetime(self):
        """
        Asynchronously block until the context deactivates.
        """
        if self._lifetime_task:
            await self._lifetime_task

    async def make(self):
        """
        Make the latex message, handling ratelimits, compilation, and output.
        """
        ctx = self.ctx
        luser = self.luser

        # Retrieve and request the user's bucket, creating if required
        if luser.id not in self.user_buckets:
            self.user_buckets[luser.id] = Bucket(5, 20)

        try:
            self.user_buckets[luser.id].request()
        except BucketOverFull:
            # A warning was already given, fail silently
            log("Aborting compile due to `BucketOverfull`.",
                context="mid:{}".format(ctx.msg.id),
                level=logging.INFO)
            return None
        except BucketFull:
            log("Aborting compile due to BucketFull`.",
                context="mid:{}".format(ctx.msg.id),
                level=logging.INFO)
            # Ratelimit warning
            await ctx.error_reply("Too many requests, please slow down!\n"
                                  "(You may try again in `5` seconds.)")
            return None

        # Retrieve the user lock, creating it if required
        if luser.id not in self.user_locks:
            self.user_locks[luser.id] = asyncio.Lock()

        async with self.user_locks[luser.id]:
            # Don't compile if the bucket is already overfull
            if self.user_buckets[luser.id].overfull:
                log("Aborting compile due to a newly overfull bucket.",
                    context="mid:{}".format(ctx.msg.id),
                    level=logging.INFO)
                return

            # Compile the source
            error = await self.compile()
            self._errors = error

            # Build header messages, presented above LaTeX output image
            if self._dm_source:
                source_message = "```fix\nLaTeX source sent via direct message.\n```"
            else:
                source_message = "```latex\n{}\n```".format(self.source.replace("```", ""))

            if error:
                self._show_emoji = self.emoji_show_errors
                self._header_shown = "{}{}Compilation error:```{}```".format(
                    self._header_name,
                    source_message,
                    error.replace("```", "")
                )
                self._header_collapsed = (
                    "{}Compile Error! "
                    "Click the {} reaction for more information.\n"
                    "(You may edit your message to recompile.)"
                ).format(
                    self._header_name,
                    self._show_emoji
                )
            else:
                self._show_emoji = self.emoji_show_source
                self._header_shown = "{}{}".format(self._header_name, source_message)
                self._header_collapsed = self._header_name

            # Fire deletion of source, if required
            if not error and self.keepsourcefor is not None:
                self._source_deletion_task = asyncio.ensure_future(self.delete_source(delay=self.keepsourcefor))
                self.ctx.tasks.append(self._source_deletion_task)

            # Obtain the output image path, potentially the failed image
            file_path = "tex/staging/{id}/{id}.png".format(id=luser.id)
            exists = True if os.path.isfile(file_path) else False
            file_path = failed_image_path if not exists else file_path

            # Build the file object for sending, possibly spoilered
            output_file = discord.File(file_path, spoiler=exists and self._spoiler_output)

            # Finally, send the output and start the reaction handler
            try:
                self._output_message = await self.ctx.reply(content=self._header_collapsed, file=output_file)
                self._lifetime_task = asyncio.ensure_future(self.activate_reactions())
                self.ctx.tasks.append(self._lifetime_task)
            except discord.Forbidden:
                pass

        return self._output_message

    async def compile(self):
        """
        Compile the source
        """
        return await self.ctx.makeTeX(self.source,
                                      self.luser.id,
                                      self.preamble,
                                      self.luser.colour,
                                      pad=not self.wide)

    async def activate_reactions(self):
        """
        Register this LatexContext as an active listener and add the reactions
        """
        ctx = self.ctx
        msg = self._output_message

        # Quit early if we can't add reactions, nothing to listen for
        if ctx.guild and not ctx.ch.permissions_for(ctx.guild.me).add_reactions:
            return

        try:
            # Register the context
            self._last_reaction = time.time()
            self.active_contexts[msg.id] = self

            # Add the emojis
            await msg.add_reaction(self.emoji_delete)
            await msg.add_reaction(self._show_emoji)
            if ctx.guild and ctx.ch.permissions_for(ctx.guild.me).manage_messages:
                await msg.add_reaction(self.emoji_delete_source)

            # Keep waiting until we have been idle longer than our lifetime
            while time.time() - self._last_reaction <= self.active_lifetime:
                await asyncio.sleep(self.active_lifetime // 2)

            # Clear the reactions we added
            if ctx.guild and ctx.ch.permissions_for(ctx.guild.me).manage_messages:
                await msg.clear_reaction(self.emoji_delete)
                await msg.clear_reaction(self._show_emoji)
                if ctx.guild and ctx.ch.permissions_for(ctx.guild.me).manage_messages:
                    await msg.clear_reaction(self.emoji_delete_source)
        except asyncio.CancelledError:
            log("LatexContext lifetime cancelled, probably due to an edit.",
                context="mid:{}".format(self.ctx.msg.id),
                level=logging.DEBUG)
            pass
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass
        except discord.HTTPException:
            pass
        finally:
            # Unregister the context
            self.active_contexts.pop(msg.id, None)

    @staticmethod
    def extract_codeblocks(text):
        """
        Extract discord-style codeblocks from provided text.
        This ignores escaping.
        """
        blocks = []

        if "```" in text:
            splits = text.split("```")
            content_blocks = [splits[i] for i in range(1, len(splits), 2)]
            for content_block in content_blocks:
                splits = content_block.split("\n", maxsplit=1)
                if len(splits) == 2 and splits[0] and ' ' not in splits[0].strip():
                    blocks.append((splits[0].strip(), splits[1].strip()))
                else:
                    blocks.append((None, content_block.strip()))
        return blocks

    @classmethod
    def parse_content(cls, content: str, mode: ParseMode):
        """
        Build potential LaTeX from message content, depending on the parse mode.
        """
        # Extract codeblocks
        codeblocks = cls.extract_codeblocks(content)
        if codeblocks:
            # Build list of relevant blocks
            blocks = [block[1] for block in codeblocks if block[0] in ['', 'tex', 'latex']]
        else:
            # Strip any wrapping backtics from content
            if content.startswith('`') and content.endswith('`'):
                content = content[1:-1]

            # No codeblocks, parse the original content
            blocks = [content]

        if blocks:
            # Parse depending on the parse mode
            if mode == ParseMode.DOCUMENT:
                source = "\n\n".join(blocks)
            elif mode == ParseMode.GATHER:
                source = "\n".join(["\\begin{{gather*}}\n{}\n\\end{{gather*}}".format(block) for block in blocks])
            elif mode == ParseMode.ALIGN:
                source = "\n".join(["\\begin{{align*}}\n{}\n\\end{{align*}}".format(block) for block in blocks])
            elif mode == ParseMode.TIKZ:
                source = "\n".join(["\\begin{{tikzpicture}}\n{}\n\\end{{tikzpicture}}".format(block) for block in blocks])
            else:
                # This should be impossible
                raise ValueError("Unknown `mode` passed to LaTeX parser.")
        else:
            # No content
            source = None

        return source

    @classmethod
    def weak_hastex(cls, content):
        r"""
        Weak Latex content checker.
        Checks whether there is a `$\S` followed by `\S$` anywhere in the content.
        (`\S` is a non-whitespace character).
        """
        if not content:
            return False

        if '$' in content and content.strip('$'):
            # Regex match for the $ pattern
            return (cls.single_dollars_pattern.search(content) is not None)
        else:
            return False

    @classmethod
    def strict_hastex(cls, content):
        r"""
        Strict Latex content checker.
        Checks for one of the following conditions:
            - At least two `$$` in the content.
            - A latex environment (by `\begin{` and `\end{`).
            - A latex mathmode macro (i.e. {`\(`, `\)`} and {`\[`, `\]`}).
        """
        if not content:
            return False

        has_tex = False

        # Check for `$$`
        has_tex = has_tex or (content.count('$$') > 1
                              and content.strip('$')
                              and cls.double_dollars_pattern.search(content) is not None)

        # Check for environments
        has_tex = has_tex or ((r"\begin{" in content) and (r"\end{" in content))

        # Check for mathmode macros
        has_tex = has_tex or ((r"\(" in content) and (r"\)" in content))
        has_tex = has_tex or ((r"\[" in content) and (r"\]" in content))

        return has_tex


async def reaction_listener(client, reaction, user):
    # Ignore reaction if it isn't from an active context
    if reaction.message.id not in LatexContext.active_contexts:
        return

    # Ignore reaction if it is from me
    if user == client.user:
        return

    # Extractions for faster lookups
    lctx = LatexContext.active_contexts.get(reaction.message.id)
    luser = lctx.luser
    ctx = lctx.ctx

    # We can't guarantee the state stays consistent through multiple awaits
    # Multiple reactions may even be used simultaneously
    # So wrap this is a general try block to avoid spitting out unhandled exceptions
    try:
        if reaction.emoji == LatexContext.emoji_delete:
            # Check permissions
            if user.id == luser.id or (ctx.guild and ctx.ch.permissions_for(user).manage_messages):
                # Cancel all tasks (in particular cancelling the activate_reactions sleep and unregistering it)
                [task.cancel() for task in ctx.tasks]

                # Delete the output message
                await reaction.message.delete()
        elif reaction.emoji in [LatexContext.emoji_show_source, LatexContext.emoji_show_errors]:
            # Check the user is the author or if they allow other people to view the source
            if user.id == luser.id or reaction.message.channel.permissions_for(user).manage_messages:
                # Toggle the shown state
                lctx._source_shown = 1 - lctx._source_shown

                # Update the message
                await reaction.message.edit(content=lctx.get_header())

                # DM if required
                if lctx._source_shown and lctx._dm_source:
                    await lctx.dm_source(user)

                # Attempt to remove the user's reaction
                if ctx.guild and ctx.ch.permissions_for(ctx.guild.me).manage_messages:
                    await reaction.remove(user)
        elif reaction.emoji == LatexContext.emoji_delete_source:
            # Check permissions
            if user.id == luser.id or (ctx.guild and ctx.ch.permissions_for(user).manage_messages):
                # Cancel any running source deletion task
                if lctx._source_deletion_task:
                    lctx._source_deletion_task.cancel()

                # Request immediate source deletion
                await lctx.delete_source()

                # Attempt to clear the reaction
                # If the reaction appears at all, we probably have manage_messages
                if ctx.guild and ctx.ch.permissions_for(ctx.guild.me).manage_messages:
                    await reaction.clear()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass


@module.init_task
def attach_emojis(client):
    LatexContext.emoji_delete = client.conf.emojis.getemoji('delete')
    LatexContext.emoji_show_source = client.conf.emojis.getemoji('latex_show_source')
    LatexContext.emoji_show_errors = client.conf.emojis.getemoji('latex_show_errors')
    LatexContext.emoji_delete_source = client.conf.emojis.getemoji('latex_delete_source')


@module.init_task
def register_reaction_listener(client: cmdClient):
    client.add_after_event("reaction_add", reaction_listener)


@module.init_task
def attach_latex_locks(client):
    # Attach user simultaneous rendering locks
    client.objects["latex_user_locks"] = LatexContext.user_locks

    # Attach user leaky buckets
    client.objects["latex_user_buckets"] = LatexContext.user_buckets
