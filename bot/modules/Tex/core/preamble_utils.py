import os
from datetime import datetime
from io import BytesIO
import asyncio
import discord

from cmdClient.lib import ResponseTimedOut, SafeCancellation, UserCancelled

from wards import is_manager, is_reviewer

from utils.lib import split_text, mail
from utils import interactive  # noqa

from ..resources import default_preamble, failed_image_path


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

preamble_test_code = r"""
ABCDEFGHIJKLMNOPQRSTUVWXYZ\\

Here is a fraction: \(\frac{1}{2}\).

Here is a display equation: \[(a+b)^2 = a^2 + b^2\]
(in fields of order $2$)
"""

# Load list of preamble presets from directory
# preset_dir = os.path.join(__location__, "presets")
# presets = [os.path.splitext(fn)[0] for fn in os.listdir(preset_dir) if fn.endswith('.tex')]
# presets_lower = [p.lower() for p in presets]


def tex_pagination(text, basetitle="", header=None, timestamp=True,
                   author=None, time=None, colour=discord.Colour.dark_blue(),
                   extra_fields=None, footer=""):
    """
    Break up source LaTeX code into a number of embedded pages,
    with the code in codeblocks of mximum 1k chars
    """
    if text:
        blocks = split_text(text, 1000, code=True, syntax="latex")
    else:
        blocks = [None]

    # Change time to a datetime object if it isn't one
    if time is None:
        time = datetime.utcnow()
    elif isinstance(time, (float, int)):
        time = datetime.fromtimestamp(time)

    blocknum = len(blocks)

    if blocknum == 1:
        block = blocks[0] if blocks[0] else None
        desc = "{}\n{}".format(header, block or "") if header else (block if block else None)

        embed = discord.Embed(title=basetitle,
                              color=colour,
                              description=desc,
                              timestamp=time)
        if author is not None:
            embed.set_author(name=author)
        if extra_fields is not None:
            for name, value in extra_fields:
                if name and value:
                    embed.add_field(name=name, value=value, inline=False)
        if footer is not None:
            embed.set_footer(text=footer)
        return [embed]

    embeds = []
    for i, block in enumerate(blocks):
        desc = "{}\n{}".format(header, block) if header else block
        embed = discord.Embed(title=basetitle,
                              colour=colour,
                              description=desc,
                              timestamp=time)
        embed.set_footer(text="{} Page {}/{}".format(footer, i+1, blocknum))
        if author is not None:
            embed.set_author(name=author)
        if extra_fields is not None:
            for name, value in extra_fields:
                if name and value:
                    embed.add_field(name=name, value=value, inline=False)
        embeds.append(embed)

    return embeds


async def sendfile_reaction_handler(ctx, msg, contents, title, file_name="preamble.tex"):
    """
    Attach a reaction to the given message which sends reacting users
    a file containing `contents`.
    """
    emoji = ctx.client.conf.emojis.getemoji("sendfile")
    try:
        await msg.add_reaction(emoji)
    except discord.Forbidden:
        return
    except discord.NotFound:
        return

    # Generate file
    temp_file = BytesIO()
    temp_file.write(contents.encode())

    def _check(reaction, user):
        return (reaction.message.id == msg.id and reaction.emoji == emoji)

    while True:
        try:
            reaction, user = await ctx.client.wait_for('reaction_add', check=_check, timeout=300)
        except asyncio.TimeoutError:
            break

        if user != ctx.client.user:
            try:
                temp_file.seek(0)
                dFile = discord.File(temp_file, filename=file_name)
                await asyncio.gather(
                    user.send(file=dFile, content=title),
                    msg.remove_reaction(emoji, user)
                )
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            except discord.NotFound:
                pass
    try:
        await msg.clear_reaction(emoji)
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass

    temp_file.close()


async def view_preamble(ctx, preamble, title, start_page=0,
                        file_react=False, file_message=None, **pagination_args):

    pages = tex_pagination(preamble, basetitle=title, **pagination_args)
    out_msg = await ctx.pager(pages, start_page=start_page, locked=False)

    if file_react and out_msg is not None:
        # Add the sendfile reaction if required
        asyncio.ensure_future(sendfile_reaction_handler(ctx, out_msg, preamble, file_message or title))

    return out_msg


async def confirm(ctx, question, preamble, **kwargs):
    out_msg = await view_preamble(ctx, preamble, "{} (y/n)".format(question), **kwargs)
    result_msg = await ctx.listen_for(["y", "yes", "n", "no"], timeout=120)

    result = result_msg.content.lower()
    try:
        await out_msg.delete()
        await result_msg.delete()
    except Exception:
        pass

    if result in ["n", "no"]:
        return False
    else:
        return True


async def preamblelog(ctx, title, user=None, userid=None, author=None, header=None, source=None):
    """
    Log a message to the preamble log channel
    """
    logchid = int(ctx.client.conf.get("preamble_logch"))

    user = user or ctx.author
    author = author or "{} ({})".format(user, user.id)

    content = "{}\n{}\n{}".format(title or "", header or "", author or "")
    if source:
        with BytesIO() as temp_file:
            temp_file.write(source.encode())
            temp_file.seek(0)
            dfile = discord.File(temp_file, filename="{}.tex".format(userid or user.id))
            await mail(
                ctx.client,
                logchid,
                content=content,
                file=dfile
            )
    else:
        await mail(
            ctx.client,
            logchid,
            content=content,
        )


#     pages = tex_pagination(source, basetitle=title, header=header, author=author)

#     if source is None:
#         await ctx.pager(pages, embed=True, locked=False, destination=logch)
#     else:
#         with BytesIO() as temp_file:
#             temp_file.write(source.encode())
#             temp_file.seek(0)
#             await ctx.pager(pages, embed=True, locked=False, destination=logch, file_data=temp_file, file_name="source.tex")


async def resolve_pending_preamble(ctx, userid, info, colour=None):
    """
    Clean up after a preamble submission request has been handled
    Involves finding the message in the submission log,
    clearing the reactions and editing it.
    """
    #     # Retrieve the pending preamble info
    #     info_pack = await ctx.bot.data.users.get(userid, "pending_preamble_info")

    #     # Return if there is no pending preamble
    #     if not info_pack:
    #         return

    #     # Retrieve the message id of the submission message
    #     msgid = info_pack[2]

    #     # Find the message in the submission channel
    #     subch = ctx.bot.objects["latex_preamble_subch"]
    #     try:
    #         msg = await ctx.bot.get_message(subch, msgid)
    #     except discord.NotFound:
    #         # The message wasn't found, just return silently, nothing to do
    #         return
    #     except Exception:
    #         # Various things could go wrong here
    #         # This step isn't crucial and we don't want to expose it to the user, so fail silently for now
    #         # TODO: Log this
    #         return

    #     # Remove all the reactions on the message
    #     await ctx.bot.clear_reactions(msg)

    #     # Edit the message with the provided info
    #     await ctx.bot.edit_message(msg, new_content=info)
    #     if colour is not None:
    #         embed = msg.embeds[0]
    #         msg_embed = discord.Embed.from_data(embed)
    #         msg_embed.colour = colour
    #         await ctx.bot.edit_message(msg, embed=msg_embed)
    pass


async def submit_preamble(ctx, user, submission, info):
    """
    Make a new preamble submission
    """
    # Submit the request
    ctx.client.data.user_pending_preambles.insert(
        allow_replace=True,
        userid=user.id,
        app=ctx.client.app,
        username=user.name,
        pending_preamble=submission,
        submission_time=int(datetime.utcnow().timestamp()),
        submission_summary=info,
        submission_source_id=ctx.author.id if not ctx.guild else ctx.guild.id,
        submission_source_name="DM" if not ctx.guild else ctx.guild.name
    )

    # Mail in the submission
    subchid = int(ctx.client.conf.get("preamble_subch"))

    with BytesIO() as temp_file:
        temp_file.write(submission.encode())
        temp_file.seek(0)
        dfile = discord.File(temp_file, filename="{}.tex".format(user.id))
        await mail(
            ctx.client,
            subchid,
            content="New submission from {} `uid:{}`".format(user, user.id),
            file=dfile
        )
#     # Mark any previous preamble request as outdated
#     await handled_preamble(ctx, user.id, "New preamble request submitted", colour=discord.Colour.red())

#     # Set the new pending preamble
#     await ctx.data.users_long.set(ctx.authid, "pending_preamble", submission)

#     # Send the preamble request to the submission channel
#     title = "New preamble submission!"
#     author = "{} ({})".format(user, user.id)
#     time = datetime.utcnow()

#     submission_channel = ctx.bot.objects["latex_preamble_subch"]
#     sub_msg = await view_preamble(ctx, submission, title, start_page=-1,
#                                   author=author, time=time, header=info,
#                                   destination=submission_channel)

#     # Store the pending preamble info
#     info_pack = (datetime.timestamp(time), info, sub_msg.id)
#     await ctx.data.users.set(ctx.authid, "pending_preamble_info", info_pack)

#     # Add the approval/denial/testing emojis to the submission
#     # Create a new context so the judgement process doesn't interfere with the original user
#     newctx = ctx.bot.make_msgctx(channel=submission_channel)
#     asyncio.ensure_future(judgement_reactions(newctx, user.id, sub_msg))


async def judgement_reactions(ctx, userid, msg):
    """
    Adds approve/deny/test reactions to the given msg,
    with the reactions applicable to the user given by the userid.
    Returns:
        None, if the userid is no longer in the pending preamble list,
        True, if the preamble was approved,
        False, if the preamble was denied.
    """
    # Check that the context author has preamble reviewer permissions
    if not await is_reviewer.run(ctx):
        raise ValueError("Attempt to add judgement reactions for non-reviewer.")

    # Load reaction emojis
    approve = ctx.client.conf.emojis.getemoji('approve')
    deny = ctx.client.conf.emojis.getemoji('deny')
    test = ctx.client.conf.emojis.getemoji('test')

    # Checks whether the emoji is valid and whether the user is the caller
    def _check(reaction, user):
        return ((reaction.emoji in [approve, deny, test]) and user == ctx.author and reaction.message == msg)

    # Add the reactions, if possible
    try:
        await msg.add_reaction(approve)
        await msg.add_reaction(deny)
        await msg.add_reaction(test)
    except discord.Forbidden:
        return

    # Reaction action loop
    while True:
        try:
            reaction, user = await ctx.client.wait_for(
                'reaction_add',
                check=_check,
                timeout=600
            )
        except asyncio.TimeoutError:
            # If the user still has a pending preamble, continue the loop
            if ctx.client.data.user_pending_preambles.select_where(userid=userid):
                continue
            else:
                # Otherwise, remove the reactions and return
                try:
                    await msg.remove_reaction(approve, ctx.client.user)
                    await msg.remove_reaction(deny, ctx.client.user)
                    await msg.remove_reaction(test, ctx.client.user)
                except Exception:
                    pass
                break

        # If the user no longer has a pending preamble, let the reviewer know and exit
        if not ctx.client.data.user_pending_preambles.select_where(userid=userid):
            await ctx.reply("Submission no longer exists!")
            return None

        # Handle the reacted emoji as appropriate
        if reaction.emoji == approve:
            if await approve_submission(ctx, userid, ctx.author):
                return True
        elif reaction.emoji == deny:
            if await deny_submission(ctx, userid, ctx.author):
                return False
        elif reaction.emoji == test:
            await test_submission(ctx, userid, ctx.author)


async def approve_submission(ctx, userid, manager, reason=None):
    ctx.author = manager  # Hack so that ask and input work properly

    # Ask for confirmation and potential new message
    # Create default approval message
    default_msg = "Your recent request for a LaTeX preamble submission has been approved!\
        \nYour preamble has been modified and may be seen using the `preamble` command.\
        \nShould you wish to revert these changes, please use `preamble --revert`."
    embed = discord.Embed(title="Preamble request approval", description=default_msg)
    embed.timestamp = datetime.utcnow()

    # If the user no longer has a pending preamble, let the reviewer know and exit
    if not ctx.client.data.user_pending_preambles.select_where(userid=userid):
        await ctx.error_reply("Submission no longer exists!")
        return None

    # Check whether this needs editing
    if reason:
        embed.add_field(name="Reviewer comments", value=reason)
        preview = await ctx.reply(content="Approving preamble...", embed=embed)
    else:
        preview = await ctx.reply(
            content=("Do you wish to add an additional message (automatically sends in 20s)? "
                     "(`y(es)`/`n(o)`/`c(ancel)`)"),
            embed=embed
        )
        try:
            result_msg = await ctx.listen_for(
                ('y', 'yes', 'n', 'no', 'c', 'cancel'),
                timeout=20
            )
            resp = result_msg.content.lower()
            try:
                await result_msg.delete()
            except discord.Forbidden:
                pass
        except ResponseTimedOut:
            resp = None

        if resp is None or resp.startswith('n'):
            # Send message as-is
            pass
        elif resp.startswith('c'):
            preview = await preview.edit(content="Preamble approval cancelled on manager request.")
            raise UserCancelled("Cancelling preamble approval.")
        elif resp.startswith('y'):
            # Ask for the new field
            try:
                result = await ctx.input("Please enter the additional approval message, or `c` to cancel!", timeout=600)
            except ResponseTimedOut:
                preview = await preview.edit(content="Preamble approval cancelled due to query timeout.")
                raise ResponseTimedOut("Query timed out, aborting preamble approval.") from None
            if result.lower() in ['c', 'cancel']:
                preview = await preview.edit(content="Preamble approval cancelled on manager request.")
                raise UserCancelled("Cancelling preamble approval.")

            # Update the embed with the new field
            embed.add_field(name="Reviewer comments", value=result)

    # Approve the preamble
    pending_info = ctx.client.data.user_pending_preambles.select_where(userid=userid)
    if not pending_info:
        preview = await preview.edit(content="User no longer has a pending preamble to approve! Cancelling.")
        raise SafeCancellation

    current_info = ctx.client.data.user_latex_preambles.select_where(userid=userid)
    previous_preamble = current_info[0]['preamble'] if current_info else default_preamble
    ctx.client.data.user_latex_preambles.insert(
        allow_replace=True,
        userid=userid,
        preamble=pending_info[0]['pending_preamble'],
        previous_preamble=previous_preamble
    )
    ctx.client.data.user_pending_preambles.delete_where(userid=userid)
    await resolve_pending_preamble(
        ctx,
        userid,
        "Preamble approved by {}".format(manager.mention),
        colour=discord.Colour.green()
    )
    await preamblelog(
        ctx,
        "Preamble request approved by {} ({})".format(manager, manager.id),
        author="{} ({})".format(pending_info[0]['username'], userid),
        userid=userid,
        source=pending_info[0]['pending_preamble']
    )

    # Update the preview
    preview = await preview.edit(
        content="Approved preamble, sending approval message {}".format(ctx.client.conf.emojis.getemoji("loading")),
        embed=embed
    )

    # Try and DM the user with their happy news
    # First find the user
    user = ctx.client.get_user(userid)
    if user is None:
        try:
            user = await ctx.client.fetch_user(userid)
        except discord.NotFound:
            await preview.edit(content="Approved, but user not known to Discord, couldn't send the approval message.")

    try:
        await user.send(embed=embed, content=user.mention)
    except discord.Forbidden:
        preview = await preview.edit(
            content=("Approved, but Discord didn't let me DM the user. "
                     "I might not be able to see them (no shared guilds), or they might have blocked me.")
        )
    except Exception as e:
        preview = await preview.edit(
            content=("Approved, but something unexpected occurred while sending the approval message.")
        )
        raise e
    else:
        preview = await preview.edit(
            content=("Preamble approved! Good work, <@{}>!".format(manager.id))
        )
    return True


async def deny_submission(ctx, userid, manager, reason=None):
    ctx.author = manager  # Hack so that ask and input work properly

    # If the user no longer has a pending preamble, let the reviewer know and exit
    if not ctx.client.data.user_pending_preambles.select_where(userid=userid):
        await ctx.error_reply("Submission no longer exists!")
        return None

    # Create base denial message
    default_msg = (
        "Your recent request for a LaTeX preamble submission was denied!\n"
        "If you want assistance setting your preamble, please join our [support guild]({})."
    ).format(ctx.client.app_info['support_guild'])
    embed = discord.Embed(title="Preamble request rejection", description=default_msg)
    embed.timestamp = datetime.utcnow()

    # Check whether this needs editing
    if reason is None:
        preview = await ctx.reply(
            content="Please enter the rejection reason, or send `c` to cancel!",
            embed=embed
        )
        try:
            result = await ctx.input(preview, delete_after=False, timeout=600)
        except ResponseTimedOut:
            preview = await preview.edit(content="Preamble rejection cancelled due to query timeout.")
            return None
        if result.lower() in ['c', 'cancel']:
            preview = await preview.edit(content="Preamble rejection cancelled on manager request.")
            raise UserCancelled("Cancelling preamble rejection.")

        # Update the embed with the new field
        embed.add_field(name="Reason", value=result)
    else:
        embed.add_field(name="Reason", value=reason)
        preview = await ctx.reply(
            content="Denying preamble.",
            embed=embed
        )

    # Deny the preamble
    pending_info = ctx.client.data.user_pending_preambles.select_where(userid=userid)
    if not pending_info:
        preview = await preview.edit(content="User no longer has a pending preamble to deny! Cancelling.")
        raise SafeCancellation

    ctx.client.data.user_pending_preambles.delete_where(userid=userid)
    await resolve_pending_preamble(
        ctx,
        userid,
        "Preamble denied by {}".format(manager.mention),
        colour=discord.Colour.red()
    )
    await preamblelog(
        ctx,
        "Preamble request denied by {} ({})".format(manager, manager.id),
        author="{} ({})".format(pending_info[0]['username'], userid),
        userid=userid,
        source=pending_info[0]['pending_preamble']
    )

    # Update the preview
    preview = await preview.edit(
        content="Denied preamble, sending rejection message {}".format(ctx.client.conf.emojis.getemoji("loading")),
        embed=embed
    )

    # First find the user
    user = ctx.client.get_user(userid)
    if user is None:
        try:
            user = await ctx.client.fetch_user(userid)
        except discord.NotFound:
            preview = await preview.edit(content="Denied, but user not known to Discord, couldn't send the rejection message.")

    try:
        await user.send(embed=embed, content=user.mention)
    except discord.Forbidden:
        preview = await preview.edit(
            content=("Denied, but Discord didn't let me DM the user. "
                     "I might not be able to see them (no shared guilds), or they might have blocked me.")
        )
    except Exception as e:
        preview = await preview.edit(
            content=("Denied, but something unexpected occurred while sending the rejection message.")
        )
        raise e
    else:
        preview = await preview.edit(
            content=("Preamble denied! Good work, <@{}>!".format(manager.id))
        )
    return True


async def test_submission(ctx, userid, manager):
    """
    Compile a piece of test LaTeX to test the provided userid's preamble.
    Replies with the compiled LaTeX output, and any error that occurs.
    """
    # Separate staging folder for testing purposes
    testid = manager.id * 10000

    # Retrieve the pending preamble if it exists, otherwise return
    pending_info = ctx.client.data.user_pending_preambles.select_where(userid=userid)
    if not pending_info:
        await ctx.error_reply("User no longer has a pending preamble to test! Cancelling.")
        raise SafeCancellation
    preamble = pending_info[0]['pending_preamble']

    # Compile the latex with this preamble
    log = await ctx.makeTeX(preamble_test_code, testid, preamble=preamble)

    file_path = "tex/staging/{id}/{id}.png".format(id=testid)
    if os.path.isfile(file_path):
        dfile = discord.File(file_path)
    else:
        dfile = discord.File(failed_image_path)

    if not log:
        message = "Test compile for pending preamble of {}.\
            \nNo errors during compile. Please check compiled image below.".format(userid)
        out_msg = await ctx.reply(content=message, file=dfile)
    else:
        message = "Test compile for pending preamble of {}.\
            \nSee the error log and output image below.".format(userid)
        embed = discord.Embed(description="```\n{}\n```".format(log))
        out_msg = await ctx.reply(content=message, file=dfile, embed=embed)

    asyncio.ensure_future(ctx.offer_delete(out_msg))
