from datetime import datetime as dt
import discord

from wards import guild_moderator, chunk_guild

from .module import guild_moderation_module as module
from .tickets import Ticket, describes_ticket, TicketType


@module.cmd("note",
            desc="Create a moderation note on a member.",
            aliases=["addnote"])
@guild_moderator()
@chunk_guild()
async def cmd_note(ctx):
    """
    Usage``:
        {prefix}note <user> [content]
    Description:
        Adds a moderator note to the specified user.
        The note will not be posted to the `modlog`, but it will appear in the user's tickets.
        Only moderators can view a user's notes.
        If `content` is not provided, you will be prompted to provide the note content.
    """
    if not ctx.args:
        return await ctx.error_reply("No arguments given, nothing to do.")

    user, *note = ctx.args.split(" ")

    # Attempt to get a user from the arguments
    user = await ctx.find_member(user, interactive=True)
    if user is None:
        return

    # If a note was provided, join the contents together.
    if note:
        note = " ".join(note)
    else:
        # No note was provided, prompt the author to provide the content.
        note = await ctx.input("Please enter the note, or `c` to cancel.")
        if note.lower() == "c":
            return await ctx.error_reply("Note creation cancelled.")

    ticket = NoteTicket.create(
        ctx.guild.id,
        ctx.author.id,
        ctx.client.user.id,
        [user.id],
        reason=note
    )
    embed = discord.Embed(description=f"Ticket #{ticket.ticketgid}: Note created for {user.mention}.")
    await ctx.reply(embed=embed)


@describes_ticket(TicketType.NOTE)
class NoteTicket(Ticket):
    @property
    def embed(self):
        """
        The note embed to be posted in the modlog.
        Overrides the original `Ticket.embed`.
        """
        # Base embed
        embed = discord.Embed(
            title="Ticket #{}".format(self.ticketgid),
            timestamp=dt.fromtimestamp(self.created_at)
        )
        embed.set_author(name="Note")

        # Moderator information
        mod_user = self._client.get_user(self.modid)
        if mod_user is not None:
            embed.set_footer(text="Created by: {}".format(mod_user), icon_url=mod_user.display_avatar)
        else:
            embed.set_footer(text="Created by: {}".format(self.modid))

        # Target information
        targets = '\n'.join("<@{0}> ({0})".format(targetid) for targetid in self.memberids)
        if len(self.memberids) == 1:
            embed.description = "`Subject`: {}".format(targets)
        else:
            embed.add_field(name="Subjects", value=targets, inline=False)

        # Reason
        if self.reason:
            embed.add_field(name='Note', value=self.reason, inline=False)

        return embed
