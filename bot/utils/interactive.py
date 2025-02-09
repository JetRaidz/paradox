import asyncio
import discord
from cmdClient import Context
from cmdClient.lib import UserCancelled, ResponseTimedOut

from .lib import paginate_list


@Context.util
async def listen_for(ctx, allowed_input=None, timeout=120, lower=True, check=None):
    """
    Listen for a one of a particular set of input strings,
    sent in the current channel by `ctx.author`.
    When found, return the message containing them.

    Parameters
    ----------
    allowed_input: Union(List(str), None)
        List of strings to listen for.
        Allowed to be `None` precisely when a `check` function is also supplied.
    timeout: int
        Number of seconds to wait before timing out.
    lower: bool
        Whether to shift the allowed and message strings to lowercase before checking.
    check: Function(message) -> bool
        Alternative custom check function.

    Returns: discord.Message
        The message that was matched.

    Raises
    ------
    cmdClient.lib.ResponseTimedOut:
        Raised when no messages matching the given criteria are detected in `timeout` seconds.
    """
    # Generate the check if it hasn't been provided
    if not check:
        # Quick check the arguments are sane
        if not allowed_input:
            raise ValueError("allowed_input and check cannot both be None")

        # Force a lower on the allowed inputs
        allowed_input = [s.lower() for s in allowed_input]

        # Create the check function
        def check(message):
            result = (message.author == ctx.author)
            result = result and (message.channel == ctx.ch)
            result = result and ((message.content.lower() if lower else message.content) in allowed_input)
            return result

    # Wait for a matching message, catch and transform the timeout
    try:
        message = await ctx.client.wait_for('message', check=check, timeout=timeout)
    except asyncio.TimeoutError:
        raise ResponseTimedOut("Session timed out waiting for user response.") from None

    return message


@Context.util
async def selector(ctx, header, select_from, timeout=120, max_len=20, allow_single=True):
    """
    Interactive routine to prompt the `ctx.author` to select an item from a list.
    Returns the list index that was selected.

    Parameters
    ----------
    header: str
        String to put at the top of each page of selection options.
        Intended to be information about the list the user is selecting from.
    select_from: List(str)
        The list of strings to select from.
    timeout: int
        The number of seconds to wait before throwing `ResponseTimedOut`.
    max_len: int
        The maximum number of items to display on each page.
        Decrease this if the items are long, to avoid going over the char limit.
    allow_single: bool
        Whether to show the selector for only one option.

    Returns
    -------
    int:
        The index of the list entry selected by the user.

    Raises
    ------
    cmdClient.lib.UserCancelled:
        Raised if the user manually cancels the selection.
    cmdClient.lib.ResponseTimedOut:
        Raised if the user fails to respond to the selector within `timeout` seconds.
    """
    # Handle improper arguments
    if len(select_from) == 0:
        raise ValueError("Selection list passed to `selector` cannot be empty.")

    # Handle having a single item to select
    if len(select_from) == 1 and not allow_single:
        return 0

    # Generate the selector pages
    footer = "Please type the number corresponding to your selection, or type `c` now to cancel."
    list_pages = paginate_list(select_from, block_length=max_len)
    pages = ["\n".join([header, page, footer]) for page in list_pages]

    # Post the pages in a paged message
    out_msg = await ctx.pager(pages)

    # Listen for valid input
    valid_input = [str(i+1) for i in range(0, len(select_from))] + ['c', 'C']
    try:
        result_msg = await ctx.listen_for(valid_input, timeout=timeout)
    except ResponseTimedOut:
        raise ResponseTimedOut("Selector timed out waiting for a response.")

    # Try and delete the selector message and the user response.
    try:
        await out_msg.delete()
        await result_msg.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass

    # Handle user cancellation
    if result_msg.content in ['c', 'C']:
        raise UserCancelled("User cancelled selection.")

    # The content must now be a valid index. Collect and return it.
    index = int(result_msg.content) - 1
    return index


@Context.util
async def multi_selector(ctx, header, select_from, timeout=120, max_len=20, allow_single=True):
    """
    Interactive routine to prompt the `ctx.author` to select multiple items from a list.
    Returns a list of list indices that were selected.

    Parameters
    ----------
    header: str
        String to put at the top of each page of selection options.
        Intended to be information about the list the user is selecting from.
    select_from: List(str)
        The list of strings to select from.
    timeout: int
        The number of seconds to wait before throwing `ResponseTimedOut`.
    max_len: int
        The maximum number of items to display on each page.
        Decrease this if the items are long, to avoid going over the char limit.
    allow_single: bool
        Whether to show the selector for only one option.

    Returns
    -------
    List[int]:
        The list of indices selected by the user.

    Raises
    ------
    cmdClient.lib.UserCancelled:
        Raised if the user manually cancels the selection.
    cmdClient.lib.ResponseTimedOut:
        Raised if the user fails to respond to the selector within `timeout` seconds.
    """
    # Handle improper arguments
    if len(select_from) == 0:
        raise ValueError("Selection list passed to `selector` cannot be empty.")

    # Handle having a single item to select
    if len(select_from) == 1 and not allow_single:
        return [0]

    # Generate the selector pages
    footer = ("Please type the numbers corresponding to your selection, "
              "separated by commas, or type `c` now to cancel. (E.g. `2, 3, 5, 7, 11`)")
    list_pages = paginate_list(select_from, block_length=max_len)
    pages = ["\n".join([header, page, footer]) for page in list_pages]

    # Post the pages in a paged message
    out_msg = await ctx.pager(pages)

    # Listen for valid input
    valid_num_strs = set(str(i+1) for i in range(0, len(select_from)))

    def _check(message):
        if not ((message.channel == ctx.ch) and (message.author == ctx.author)):
            return False
        if not message.content:
            return False

        content = message.content.lower()
        if (content == 'c') or all(chars.strip() in valid_num_strs for chars in content.split(',')):
            return True
        else:
            return False

    try:
        result_msg = await ctx.client.wait_for('message', check=_check, timeout=timeout)
    except asyncio.TimeoutError:
        raise ResponseTimedOut("Selector timed out waiting for a response.")

    # Try and delete the selector message and the user response.
    try:
        await out_msg.delete()
        await result_msg.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass

    # Handle user cancellation
    if result_msg.content in ['c', 'C']:
        raise UserCancelled("User cancelled selection.")

    # The content must now be a valid set of indicies. Collect and return it.
    index = [int(chars.strip()) - 1 for chars in result_msg.content.split(',')]
    return index


@Context.util
async def pager(ctx, pages, locked=True, blocking=False, destination=None, start_page=0, **kwargs):
    """
    Shows the user each page from the provided list `pages` one at a time,
    providing reactions to page back and forth between pages.
    This is done asynchronously, and returns after displaying the first page.

    Parameters
    ----------
    pages: List(Union(str, discord.Embed))
        A list of either strings or embeds to display as the pages.
    locked: bool
        Whether only the `ctx.author` should be able to use the paging reactions.
    blocking: bool
        Whether to block until the pager has finished.
        Useful for cancelling tasks when the pager completes.
    destination: Optional[discord.Messageable]
        Optional custom destination to use instead of `ctx.ch`.
    start_page: Optional[int]
        Optional initial page to display.
    kwargs: ...
        Remaining keyword arguments are transparently passed to the sender method.

    Returns: discord.Message
        This is the output message, returned for easy deletion.
    """
    # Handle broken input
    if len(pages) == 0:
        raise ValueError("Pager cannot page with no pages!")

    # Identify sender method based on destination
    if destination is None or destination == ctx.ch:
        sender = ctx.reply
    else:
        sender = destination.send

    # Post first page. Method depends on whether the page is an embed or not.
    if isinstance(pages[0], discord.Embed):
        out_msg = await sender(embed=pages[start_page], **kwargs)
    else:
        out_msg = await sender(pages[start_page], **kwargs)

    # Run the paging loop if required
    if len(pages) > 1:
        task = asyncio.ensure_future(_pager(ctx, out_msg, pages, locked, start_page=start_page))
        if blocking:
            await task

    # Return the output message
    return out_msg


async def _pager(ctx, out_msg, pages, locked, start_page=0):
    """
    Asynchronous initialiser and loop for the `pager` utility above.
    """
    # Page number
    page = start_page

    # Add reactions to the output message
    next_emoji = ctx.client.conf.emojis.getemoji("next", "▶")
    prev_emoji = ctx.client.conf.emojis.getemoji("prev", "◀")

    try:
        await out_msg.add_reaction(prev_emoji)
        await out_msg.add_reaction(next_emoji)
    except discord.Forbidden:
        # We don't have permission to add paging emojis
        # Die as gracefully as we can
        await ctx.error_reply("Cannot page results because I do not have permissions to react!")
        return

    # Check function to determine whether a reaction is valid
    def check(reaction, user):
        result = reaction.message.id == out_msg.id
        result = result and reaction.emoji in [next_emoji, prev_emoji]
        result = result and not (user.id == ctx.client.user.id)
        result = result and not (locked and user != ctx.author)
        return result

    # Begin loop
    while True:
        # Wait for a valid reaction, break if we time out
        try:
            reaction, user = await ctx.client.wait_for('reaction_add', check=check, timeout=300)
        except asyncio.TimeoutError:
            break
        except asyncio.CancelledError:
            break

        # Attempt to remove the user's reaction, silently ignore errors
        asyncio.ensure_future(_safe_async_future(out_msg.remove_reaction(reaction.emoji, user)))

        # Change the page number
        page += 1 if reaction.emoji == next_emoji else -1
        page %= len(pages)

        # Edit the message with the new page
        active_page = pages[page]
        if isinstance(active_page, discord.Embed):
            out_msg = await out_msg.edit(embed=active_page)
        else:
            out_msg = await out_msg.edit(content=active_page)

    # Clean up by removing the reactions
    try:
        await out_msg.clear_reactions()
    except discord.Forbidden:
        try:
            await out_msg.remove_reaction(next_emoji, ctx.client.user)
            await out_msg.remove_reaction(prev_emoji, ctx.client.user)
        except discord.NotFound:
            pass
    except discord.NotFound:
        pass


async def _safe_async_future(future):
    """
    Waits for the given future and ignores any errors that arise.
    Use inside `asyncio.ensure_future` to silence errors.
    """
    try:
        await future
    except Exception:
        pass


@Context.util
async def input(ctx, msg=None, delete_after=True, timeout=120):
    """
    Listen for a response in the current channel, from ctx.author.
    Returns the response from ctx.author, if it is provided.
    Parameters
    ----------
    msg: Optional[Union[string, discord.Message]]
        When given a `Message`, treats it as the prompt message.
        When given a string, sends the message and uses it as the prompt message.
        Will use a default message if not provided.
    delete_after: bool
        Whether to delete the prompt message after input is given.
    timeout: int
        Number of seconds to wait before timing out.
    Raises
    ------
    cmdClient.lib.ResponseTimedOut:
        Raised when ctx.author does not provide a response before the function times out.
    """
    # Deliver prompt
    if msg is None or isinstance(msg, str):
        offer_msg = await ctx.reply(msg or "Please enter your input.")
    elif isinstance(msg, discord.Message):
        offer_msg = msg
    else:
        raise ValueError("Invalid prompt message given.")

    # Criteria for the input message
    def checks(m):
        return m.author == ctx.author and m.channel == ctx.ch

    # Listen for the reply
    try:
        result_msg = await ctx.client.wait_for("message", check=checks, timeout=timeout)
    except asyncio.TimeoutError:
        raise ResponseTimedOut("Session timed out waiting for user response.") from None

    result = result_msg.content

    # Attempt to delete the prompt and reply messages
    if delete_after:
        try:
            await offer_msg.delete()
            await result_msg.delete()
        except Exception:
            pass

    return result


@Context.util
async def ask(ctx, msg, timeout=30, use_msg=None, add_hints=True, del_on_timeout=False):
    """
    Ask ctx.author a yes/no question.
    Returns 0 if ctx.author answers no
    Returns 1 if ctx.author answers yes
    Parameters
    ----------
    msg: string
        Adds the question to the message string.
        Requires an input.
    timeout: int
        Number of seconds to wait before timing out.
    use_msg: discord.Message
        Edit a pre-sent message with the prompt, instead of sending a new message.
    add_hints: bool
        Whether to add the answer hints to the prompt.
    del_on_timeout: bool
        Whether to delete the question if it times out.
    Raises
    ------
    Nothing
    """
    out = "{} {}".format(msg, "`y(es)`/`n(o)`") if add_hints else msg

    offer_msg = use_msg or await ctx.reply(out)
    if use_msg:
        use_msg = await use_msg.edit(content=msg)

    result_msg = await ctx.listen_for(["y", "yes", "n", "no"], timeout=timeout)

    if result_msg is None:
        if del_on_timeout:
            try:
                await offer_msg.delete()
            except Exception:
                pass
        return None
    result = result_msg.content.lower()
    try:
        if not use_msg:
            await offer_msg.delete()
        await result_msg.delete()
    except Exception:
        pass
    if result in ["n", "no"]:
        return 0
    return 1
