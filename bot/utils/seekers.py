import asyncio
import discord
from cmdClient import Context
from cmdClient.lib import InvalidContext, UserCancelled, ResponseTimedOut, SafeCancellation
from . import interactive as _interactive  # noqa


@Context.util
async def find_role(ctx, userstr, create=False, interactive=False, collection=None, allow_notfound=True):
    """
    Find a guild role given a partial matching string,
    allowing custom role collections and several behavioural switches.

    Parameters
    ----------
    userstr: str
        String obtained from a user, expected to partially match a role in the collection.
        The string will be tested against both the id and the name of the role.
    create: bool
        Whether to offer to create the role if it does not exist.
        The bot will only offer to create the role if it has the `manage_channels` permission.
    interactive: bool
        Whether to offer the user a list of roles to choose from,
        or pick the first matching role.
    collection: List[Union[discord.Role, discord.Object]]
        Collection of roles to search amongst.
        If none, uses the guild role list.
    allow_notfound: bool
        Whether to return `None` when there are no matches, instead of raising `SafeCancellation`.
        Overriden by `create`, if it is set.

    Returns
    -------
    discord.Role:
        If a valid role is found.
    None:
        If no valid role has been found.

    Raises
    ------
    cmdClient.lib.UserCancelled:
        If the user cancels interactive role selection.
    cmdClient.lib.ResponseTimedOut:
        If the user fails to respond to interactive role selection within `60` seconds`
    cmdClient.lib.SafeCancellation:
        If `allow_notfound` is `False`, and the search returned no matches.
    """
    # Handle invalid situations and input
    if not ctx.guild:
        raise InvalidContext("Attempt to use find_role outside of a guild.")

    if userstr == "":
        raise ValueError("User string passed to find_role was empty.")

    # Create the collection to search from args or guild roles
    collection = collection if collection is not None else ctx.guild.roles

    # If the unser input was a number or possible role mention, get it out
    userstr = userstr.strip()
    roleid = userstr.strip('<#@&!> ')
    roleid = int(roleid) if roleid.isdigit() else None
    searchstr = userstr.lower()

    # Find the role
    role = None

    # Check method to determine whether a role matches
    def check(role):
        return (role.id == roleid) or (searchstr in role.name.lower())

    # Get list of matching roles
    roles = list(filter(check, collection))

    if len(roles) == 0:
        # Nope
        role = None
    elif len(roles) == 1:
        # Select our lucky winner
        role = roles[0]
    else:
        # We have multiple matching roles!
        if interactive:
            # Interactive prompt with the list of roles, handle `Object`s
            role_names = [
                role.name if isinstance(role, discord.Role) else str(role.id) for role in roles
            ]

            try:
                selected = await ctx.selector(
                    "`{}` roles found matching `{}`!".format(len(roles), userstr),
                    role_names,
                    timeout=60
                )
            except UserCancelled:
                raise UserCancelled("User cancelled role selection.") from None
            except ResponseTimedOut:
                raise ResponseTimedOut("Role selection timed out.") from None

            role = roles[selected]
        else:
            # Just select the first one
            role = roles[0]

    # Handle non-existence of the role
    if role is None:
        msgstr = "Couldn't find a role matching `{}`!".format(userstr)
        if create:
            # Inform the user
            msg = await ctx.error_reply(msgstr)
            if ctx.guild.me.guild_permissions.manage_roles:
                # Offer to create it
                resp = await ctx.ask("Would you like to create this role?", timeout=30)
                if resp:
                    # They accepted, create the role
                    # Before creation, check if the role name is too long
                    if len(userstr) > 100:
                        await ctx.error_reply("Could not create a role with a name over 100 characters long!")
                    else:
                        role = await ctx.guild.create_role(
                            name=userstr,
                            reason="Interactive role creation for {} (uid:{})".format(ctx.author, ctx.author.id)
                        )
                        await msg.delete()
                        await ctx.reply("You have created the role `{}`!".format(userstr))

            # If we still don't have a role, cancel unless allow_notfound is set
            if role is None and not allow_notfound:
                raise SafeCancellation
        elif not allow_notfound:
            raise SafeCancellation(msgstr)
        else:
            await ctx.error_reply(msgstr)

    return role


@Context.util
async def find_channel(ctx, userstr, interactive=False, collection=None, chan_type=None):
    """
    Find a guild channel given a partial matching string,
    allowing custom channel collections and several behavioural switches.

    Parameters
    ----------
    userstr: str
        String obtained from a user, expected to partially match a channel in the collection.
        The string will be tested against both the id and the name of the channel.
    interactive: bool
        Whether to offer the user a list of channels to choose from,
        or pick the first matching channel.
    collection: List(discord.Channel)
        Collection of channels to search amongst.
        If none, uses the full guild channel list.
    chan_type: discord.ChannelType
        Type of channel to restrict the collection to.

    Returns
    -------
    discord.Channel:
        If a valid channel is found.
    None:
        If no valid channel has been found.

    Raises
    ------
    cmdClient.lib.UserCancelled:
        If the user cancels interactive channel selection.
    cmdClient.lib.ResponseTimedOut:
        If the user fails to respond to interactive channel selection within `60` seconds`
    """
    # Handle invalid situations and input
    if not ctx.guild:
        raise InvalidContext("Attempt to use find_channel outside of a guild.")

    if userstr == "":
        raise ValueError("User string passed to find_channel was empty.")

    # Create the collection to search from args or guild channels
    if collection is None:
        collection = []

        for ch in ctx.guild.channels:
            collection.append(ch)

        for ch in ctx.guild.threads:
            collection.append(ch)

    if chan_type is not None:
        collection = [chan for chan in collection if chan.type == chan_type]

    # If the user input was a number or possible channel mention, extract it
    chanid = userstr.strip('<#@&!>')
    chanid = int(chanid) if chanid.isdigit() else None
    searchstr = userstr.lower()

    # Find the channel
    chan = None

    # Check method to determine whether a channel matches
    def check(chan):
        return (chan.id == chanid) or (searchstr in chan.name.lower())

    # Get list of matching channels
    channels = list(filter(check, collection))

    if len(channels) == 0:
        # Nope
        chan = None
    elif len(channels) == 1:
        # Select our lucky winner
        chan = channels[0]
    else:
        # We have multiple matching channels!
        if interactive:
            # Interactive prompt with the list of channels
            chan_names = [f"{chan.name:<24} {str(chan.type):<12}" for chan in channels]

            try:
                selected = await ctx.selector(
                    "`{}` channels found matching `{}`!".format(len(channels), userstr),
                    chan_names,
                    timeout=60
                )
            except UserCancelled:
                raise UserCancelled("User cancelled channel selection.") from None
            except ResponseTimedOut:
                raise ResponseTimedOut("Channel selection timed out.") from None

            chan = channels[selected]
        else:
            # Just select the first one
            chan = channels[0]

    if chan is None:
        await ctx.error_reply("Couldn't find a channel matching `{}`!".format(userstr))

    return chan


@Context.util
async def find_member(ctx, userstr, interactive=False, collection=None, collection_limit=1000, silent_notfound=False):
    """
    Find a guild member given a partial matching string,
    allowing custom member collections.

    Parameters
    ----------
    userstr: str
        String obtained from a user, expected to partially match a member in the collection.
        The string will be tested against both the userid, full user name and user nickname.
    interactive: bool
        Whether to offer the user a list of members to choose from,
        or pick the first matching member.
    collection: List(discord.Member)
        Collection of members to search amongst.
        If none, uses the full guild member list.
    collection_limit: int
        Limit the collection to X members.
        Queries over this limit will return a SafeCancellation.
        Default collection limit is 1000.
    silent_notfound: bool
        Whether to not reply with a not-found error when there are no matches.
        Allows custom handling for this case.

    Returns
    -------
    discord.Member:
        If a valid member is found.
    None:
        If no valid member has been found.

    Raises
    ------
    cmdClient.lib.UserCancelled:
        If the user cancels interactive member selection.
    cmdClient.lib.ResponseTimedOut:
        If the user fails to respond to interactive member selection within `60` seconds`
    """
    # Handle invalid situations and input
    if not ctx.guild:
        raise InvalidContext("Attempt to use find_member outside of a guild.")

    if userstr == "":
        raise ValueError("User string passed to find_member was empty.")

    # Create the collection to search from args or guild members
    collection = collection if collection is not None else ctx.guild.members

    # If the user input was a number or possible member mention, extract it
    userid = userstr.strip('<#@&!>')
    userid = int(userid) if userid.isdigit() else None
    searchstr = userstr.lower()

    # Find the member
    member = None

    # Check method to determine whether a member matches
    def check(member):
        return (
            member.id == userid
            or searchstr in member.display_name.lower()
            or searchstr in str(member).lower()
        )

    # Get list of matching members
    members = list(filter(check, collection))

    if len(members) > collection_limit:
        raise SafeCancellation("Too many matching members found! Please refine your input and try again.")

    if len(members) == 0:
        # Nope
        member = None
    elif len(members) == 1:
        # Select our lucky winner
        member = members[0]
    else:
        # We have multiple matching members!
        if interactive:
            # Interactive prompt with the list of members
            member_names = [
                "{} {}".format(
                    member.nick if member.nick else member,
                    ("({})".format(member)) if member.nick else ""
                ) for member in members
            ]

            try:
                selected = await ctx.selector(
                    "`{}` members found matching `{}`!".format(len(members), userstr),
                    member_names,
                    timeout=60
                )
            except UserCancelled:
                raise UserCancelled("User cancelled member selection.") from None
            except ResponseTimedOut:
                raise ResponseTimedOut("Member selection timed out.") from None

            member = members[selected]
        else:
            # Just select the first one
            member = members[0]

    if member is None and not silent_notfound:
        await ctx.error_reply("Couldn't find a member matching `{}`!".format(userstr))

    return member


@Context.util
async def find_message(ctx, msgid, chlist=None, ignore=[]):
    """
    Searches for the given message id in the guild channels.

    Parameters
    -------
    msgid: int
        The `id` of the message to search for.
    chlist: Optional[List[discord.TextChannel]]
        List of channels to search in.
        If `None`, searches all the text channels that the `ctx.author` can read.
    ignore: list
        A list of channelids to explicitly ignore in the search.

    Returns
    -------
    Optional[discord.Message]:
        If a message is found, returns the message.
        Otherwise, returns `None`.
    """
    if not ctx.guild:
        raise InvalidContext("Cannot use this seeker outside of a guild!")

    msgid = int(msgid)

    # Build the channel list to search
    if chlist is None:
        chlist = [ch for ch in ctx.guild.text_channels if ch.permissions_for(ctx.author).read_messages]

    # Remove any channels we are ignoring
    chlist = [ch for ch in chlist if ch.id not in ignore]

    tasks = set()

    i = 0
    while True:
        done = set((task for task in tasks if task.done()))
        tasks = tasks.difference(done)

        results = [task.result() for task in done]

        result = next((result for result in results if result is not None), None)
        if result:
            [task.cancel() for task in tasks]
            return result

        if i < len(chlist):
            task = asyncio.create_task(_search_in_channel(chlist[i], msgid))
            tasks.add(task)
            i += 1
        elif len(tasks) == 0:
            return None

        await asyncio.sleep(0.25)


async def _search_in_channel(channel: discord.TextChannel, msgid: int):
    if channel.type != discord.ChannelType.text:
        return

    try:
        message = await channel.fetch_message(msgid)
    except Exception:
        return None
    else:
        return message
