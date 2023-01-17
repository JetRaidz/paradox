import asyncio
from datetime import datetime as dt

import discord
from wards import guild_moderator, chunk_guild

from .module import guild_moderation_module as module
from .tickets import Ticket


@module.cmd("tickets",
            desc="List a user's moderation tickets.")
@guild_moderator()
@chunk_guild()
async def cmd_tickets(ctx):
    """
    Usage``:
        {prefix}tickets <member | userid>
    Description:
        List the tickets associated to the given user.
        If the user is not in the server, it must be provided by userid.

        While viewing the ticket list, type the number of the ticket or click the ticket number to view the full ticket.

        To use this command, you need to be a **guild moderator**.\
            That is, you need to have the `manage_guild` permission or the configured `modrole`.
    """
    if not ctx.args:
        return await ctx.error_reply("Please provide a member or userid to show tickets for.")

    # Find the provided user
    user = await ctx.find_member(ctx.args, interactive=True, silent_notfound=True)
    if user is None:
        if not ctx.args.isdigit():
            return await ctx.error_reply("No members found matching `{}`!".format(ctx.args))
        else:
            userid = int(ctx.args)
    else:
        userid = user.id

    # Fetch the tickets for the given user
    tickets = Ticket.fetch_tickets_where(guildid=ctx.guild.id, memberid=userid)
    if not tickets:
        return await ctx.error_reply("No tickets found for `{}`!".format(user or userid))
    tickets.reverse()

    # Build the ticket list pages
    title = "Tickets for {}".format(user or userid)
    ticket_lines = ["[#{}]({}) ⎪ {} ⎪ `{:<8}` ⎪ {}".format(
        ticket.ticketgid,
        ticket.jumpto,
        dt.fromtimestamp(ticket.created_at).strftime("%d/%m/%y"),
        ticket._ticket_type.name,
        ticket.reason.splitlines()[0] if len(ticket.reason.splitlines()[0]) < 45
        else ticket.reason.splitlines()[0][:42] + '...'
    ) for ticket in tickets]
    pages = ['\n'.join(ticket_lines[i: i+10]) for i in range(0, len(ticket_lines), 10)]
    embeds = [
        discord.Embed(title=title, description=page).set_footer(text="Page {}/{}".format(p+1, len(pages)))
        for p, page in enumerate(pages)
    ]

    out_msg = await ctx.pager(embeds, content="Type a ticket number to see the full ticket.")

    display_task = asyncio.create_task(_ticket_display(ctx, tickets))
    await _offer_cancel(
        ctx,
        out_msg,
        display_task
    )
    try:
        await out_msg.edit(content="")
        await out_msg.clear_reactions()
    except Exception:
        pass


async def _offer_cancel(ctx, msg, *tasks, timeout=300):
    """
    Add a cancel reaction to the given `msg` to cancel the given tasks.
    Cancels the tasks after the reaction is pressed or upon timout.
    """
    # Get the cancel emoji
    emoji = ctx.client.conf.emojis.getemoji("cancel", "❌")

    try:
        # Add the reaction to the message
        await msg.add_reaction(emoji)

        # Wait for the user to press the reaction
        reaction, user = await ctx.client.wait_for(
            "reaction_add",
            check=lambda r, u: (r.message == msg and r.emoji == emoji and u == ctx.author),
            timeout=timeout
        )

        # Remove the reaction
        await msg.clear_reaction(emoji)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        # Timed out or cancelled waiting for the reaction, attempt to remove the reaction
        try:
            await msg.remove_reaction(emoji, ctx.client.user)
        except Exception:
            pass
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass
    finally:
        # Cancel the tasks
        for task in tasks:
            if not task.done() or task.cancelled():
                task.cancel()


async def _ticket_display(ctx, tickets):
    """
    Display tickets when the ticket number is entered.
    """
    ticket_map = {ticket.ticketgid: ticket for ticket in tickets}
    current_ticket_msg = None

    try:
        while True:
            # Wait for a number
            try:
                result = await ctx.client.wait_for(
                    "message",
                    check=lambda msg: (msg.author == ctx.author
                                       and msg.channel == ctx.ch
                                       and msg.content.isdigit()
                                       and int(msg.content) in ticket_map)
                )
            except asyncio.TimeoutError:
                return

            # Delete the response
            try:
                await result.delete()
            except discord.HTTPException:
                pass

            # Display the ticket
            embed = ticket_map[int(result.content)].embed
            if current_ticket_msg:
                try:
                    await current_ticket_msg.edit(embed=embed)
                except discord.HTTPException:
                    current_ticket_msg = None

            if not current_ticket_msg:
                try:
                    current_ticket_msg = await ctx.reply(embed=embed)
                except discord.HTTPException:
                    return
                asyncio.create_task(ctx.offer_delete(current_ticket_msg))

    except asyncio.CancelledError:
        return


async def _kill_after(control_task, *dependent_tasks):
    await control_task
    for dependent_task in dependent_tasks:
        if not dependent_task.done() and not dependent_task.cancelled():
            dependent_task.cancel()
