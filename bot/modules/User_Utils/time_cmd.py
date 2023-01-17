import discord
from datetime import datetime
from pytz import timezone, all_timezones
import itertools
import random

from utils.lib import paginate_list
from utils import seekers, interactive  # noqa
from wards import chunk_guild

from .module import utils_module as module

from .countrymap import countries
from . import time_data as tdata # noqa

"""
Provides a time command for setting user timezone and displaying time.

Commands provided:
    time:
        Display the author or another user's time, and interactively set timezone.
User data:
    tz: string (valid timezone)
        (app independent, user configured)
        The user's timezone in pytz format.
"""

# Some quotes about time
time_quotes = [
    "\"Men talk of killing time, while time quietly kills them.\" -- Dion Boucicault",
    "\"Time brings all things to pass.\" -- Aeschylus",
    "\"Time is a storm in which we are all lost.\" -- William Carlos Williams",
    "\"The trouble is, you think you have time.\" -- Jack Kornfield",
    "\"The only reason for time is so that everything doesn’t happen at once.\" -- Albert Einstein",
    "\"Who controls the past, controls the future: who controls the present controls the past.\" -- George Orwell",
    "\"They always say time changes things, but you actually have to change them yourself.\" -- Andy Warhol",
    "\"There’s never enough time to do all the nothing you want.\" -- Bill Watterson",
    "\"It’s not that we have little time, but more that we waste a good deal of it.\" -- Seneca"
]

# Generate list of countries per continent and the continent name list
cont_dict = {}
for country in countries:
    if country['continent'] not in cont_dict:
        cont_dict[country['continent']] = [country]
    else:
        cont_dict[country['continent']].append(country)
continents = [{"name": name, "countries": countries} for name, countries in cont_dict.items()]
cont_names = [c['name'] for c in continents]


def get_time(tz):
    """
    Get a datetime object representing the current time in the given timezone.
    """
    TZ = timezone(tz)
    return datetime.now(TZ)


def gen_tz_strings(tzlist):
    """
    Generates blocks of timezone (time) pairs with nice spacing, ready for use in a pager.
    """
    tzlist = [(tz, get_time(tz).strftime('%I:%M %p')) for tz in tzlist]
    tz_blocks = [tzlist[i:i + 20] for i in range(0, len(tzlist), 20)]
    max_block_lens = [len(max(list(zip(*tz_block))[0], key=len)) for tz_block in tz_blocks]
    block_strs = [
        ["{0[0]:^{max_len}} {0[1]:^10}".format(tzpair, max_len=max_block_lens[i]) for tzpair in tzblock]
        for i, tzblock in enumerate(tz_blocks)
    ]
    blocks = list(itertools.chain(*block_strs))
    return blocks


async def tz_lookup(ctx, search_str):
    """
    Intelligently Lookup a timezone from a given partial or full string.
    """
    # If the search string already has a valid timezone, great
    if search_str in all_timezones:
        return search_str

    search_str = search_str.lower()
    # Generate timezone list for searching
    searchlist = [
        (tz, "{} {} {}".format(tz, get_time(tz).strftime('%I:%M%p'), get_time(tz).strftime('%H:%M')).lower())
        for tz in all_timezones
    ]

    options = []
    if ':' in search_str:
        # If it has a colon it's probably a time
        search_str = search_str.replace(' ', '')

        # Look for this time in the search list
        options = [tz for tz, tzstr in searchlist if search_str in tzstr]
        if not options:
            # Time not found. Try to get the last digit and increase it by one, then look again.
            if search_str[-1].isdigit():
                search_str = search_str[:-1] + str(int(search_str[-1]) + 1)
                options = [tz for tz, tzstr in searchlist if search_str in tzstr]
            elif search_str[-3].isdigit():
                search_str = search_str[:-3] + str(int(search_str[-3]) + 1) + search_str[-2:]
                options = [tz for tz, tzstr in searchlist if search_str in tzstr]
    else:
        # So it's not a time, just some string.
        search_str = search_str.replace(' ', '_')

        # Look for this in the search list
        options = [tz for tz, tzstr in searchlist if search_str in tzstr]

    if options:
        # Yay we found some matches
        tzid = await ctx.selector(
            "Multiple matching timezones found, please select one!",
            gen_tz_strings(options),
            allow_single=False
        )
        return options[tzid] if tzid is not None else None
    else:
        # Nope, we tried our best but couldn't find any matches
        await ctx.reply("No matching timezones were found!")
        return None


async def tz_picker(ctx):
    """
    Interactive timezone selector for setting the author's timezone.
    """
    contid = await ctx.selector("Please select your continent.", cont_names)
    if contid is None:
        return None

    countries = continents[contid]['countries']
    countrynames = [c['name'] for c in countries]
    countryid = await ctx.selector("Please select your country", countrynames)
    if countryid is None:
        return None

    timezones = countries[countryid]['timezones']
    timezone_strs = gen_tz_strings(timezones)
    tzid = await ctx.selector("Please select your timezone", timezone_strs)

    return timezones[tzid] if tzid is not None else None


def get_timestr(tz, brief=False):
    """
    Get the current time in the given timezone, using a fixed format string.
    """
    format_str = "**%H:%M, %d/%m/%Y**" if brief else "**%I:%M %p (%Z)** on **%a, %d/%m/%Y**"
    return get_time(tz).strftime(format_str)


async def time_diff(ctx, tz, auth_tz, brief=False):
    """
    Get a string representing the time difference between the user's timezone and the given one.
    """
    if auth_tz is None or tz is None:
        return None
    author_time = get_time(auth_tz)
    other_time = get_time(tz)
    timediff = other_time.replace(tzinfo=None) - author_time.replace(tzinfo=None)
    diffsecs = round(timediff.total_seconds())
    name = ctx.author.name

    if diffsecs == 0:
        return ", the same as **{}**!".format(name)

    modifier = "behind" if diffsecs > 0 else "ahead"
    diffsecs = abs(diffsecs)

    hours, remainder = divmod(diffsecs, 3600)
    mins, _ = divmod(remainder, 60)

    hourstr = "{} hour{} ".format(hours, "s" if hours > 1 else "") if hours else ""
    minstr = "{} minutes ".format(mins) if mins else ""
    joiner = "and " if (hourstr and minstr) else ""
    return ".\n**{}** is {}{}{}{}, at {}.".format(
        name, hourstr, joiner, minstr, modifier, get_timestr(auth_tz, brief=brief)
    )


@module.cmd("time",
            desc="Displays the current time for a user",
            flags=['set', 'at', 'list', 'brief', '24h', 'reset'],
            aliases=['ti'])
@chunk_guild()
async def cmd_time(ctx, flags):
    """
    Usage``:
        {prefix}time [user]
        {prefix}time --set [timezone or time]
        {prefix}time --at <timezone>
        {prefix}time --brief
        {prefix}time --list
        {prefix}time --reset
    Description:
        Shows the current time for yourself or the provided user.
        Use the `set` flag to interactively pick your timezone from the international tz database.
        You can also view the time in a particular timezone using the `at` flag.
        The `at` flag also allows you to see a list of timezones with a specific given time.
    Flags::
        at: Shows the current time in the timezone given. (Can be a partial timezone)
        brief: Toggles usage of a briefer time display.
        list: Displays a list of valid timezones in the tz database, as shown [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).
        reset: Resets the currently set timezone. This cannot be undone. 
        set: Sets your timezone to the one provided, or shows an interactive timezone picker.
    Examples``:
        {prefix}time {ctx.msg.author.name}
        {prefix}time --set
        {prefix}time --set Australia/Melbourne
        {prefix}time --set Australia
        {prefix}time --at Melbourne
        {prefix}time --at 06:00
    """
    prefix = ctx.best_prefix()

    time_data = ctx.client.data.user_time_settings
    tauthor = time_data.select_where(userid=ctx.author.id)
    brief = tauthor[0]['brief_display'] if tauthor else False
    auth_tz = tauthor[0]['timezone'] if tauthor else None

    if flags["set"]:
        # Handling setting a timezone
        # Grab the timezone from interactive lookup if args are given, otherwise the interactive picker
        tz = (await tz_lookup(ctx, ctx.args)) if ctx.args else (await tz_picker(ctx))

        if tz:
            # We have a timezone, display the success message, current time, and a warning about Etc if needed.
            user_time = get_timestr(tz, brief=brief)
            msg = "Your timezone has been set to `{}`!\nYour current time is {}.".format(tz, user_time)
            if ctx.args and (tz.startswith("Etc/GMT+") or tz.startswith("Etc/GMT-")):
                other_tz = tz.replace("+", "-").replace("-", "+")
                other_time = get_timestr(other_tz, brief=brief)
                proper_time = other_tz[4:]
                warning = (
                    "\nNote that due to the POSIX standard, the timezone `{}` represents the time in `{}`.\n"
                    "If your time is incorrect, consider setting your timezone to `{}`, "
                    "where the time is currently {}.\n"
                    "You can read more about the standard at https://en.wikipedia.org/wiki/Tz_database#Area."
                ).format(tz, proper_time, other_tz, other_time)

                msg += warning

            time_data.upsert(
                constraint='userid',
                userid=ctx.author.id,
                timezone=tz
            )
            await ctx.reply(msg)
        else:
            # We failed to get a timezone, post setting help.
            setter_help = "Need help setting your timezone? One of the following might help!"
            methods = []
            if ctx.args:
                methods.append("Try using our interactive timezone picker with `{prefix}ti --set`")
            else:
                methods.append("Try entering the name of your nearest capital city, e.g. `{prefix}ti --set London`, "
                               "or your current time, e.g. `{prefix}ti --set 7:20`.")
            methods.append("Find your timezone in the complete list with `{prefix}ti --list`")
            methods.append(
                "Use [this interactive map](http://kevalbhatt.github.io/timezone-picker) to find your timezone!"
            )
            methods.append(
                "Get your timezone from your country and region "
                "[here](http://www.timezoneconverter.com/cgi-bin/findzone)!"
            )
            methods.append("Or join our [support server]({support}) and ask one of our friendly support team!")

            desc = ("\n".join(methods)).format(prefix=prefix, support=ctx.client.app_info["support_guild"])
            embed = discord.Embed(title=setter_help, description=desc, colour=discord.Colour.green())
            await ctx.reply(embed=embed)
    elif flags['at']:
        # Handle getting the time at a given timezone
        if not ctx.args:
            # No timezone was given, grumble and return
            # TODO: adapt interactive picker for this
            await ctx.reply(
                "Usage: `{prefix}ti --at <timezone>`, e.g. `{prefix}ti --at Melbourne`".format(prefix=prefix)
            )
        else:
            # Lookup the timezone
            tz = await tz_lookup(ctx, ctx.args)
            if not tz:
                # Timezone lookup failed, the lookup will have already grumbled so just pass on
                pass
            else:
                # Report the time, with the time difference if possible
                tdiffstr = await time_diff(ctx, tz, auth_tz, brief=brief)
                timestr = get_timestr(tz, brief=brief)

                msg = "The time in `{}` is {}{}".format(tz, timestr, tdiffstr or '.')
                await ctx.reply(msg)
    elif flags['list']:
        await ctx.offer_delete(await ctx.pager(paginate_list(gen_tz_strings(all_timezones), title="Timezone list")))
    elif flags['brief']:
        brief = 1 - brief
        time_data.upsert(
            constraint='userid',
            userid=ctx.author.id,
            brief_display=bool(brief)
        )
        await ctx.reply("Your clock is now more compact." if brief else "Your clock is now more verbose.")
    elif flags['reset']:
        # Add a confirmation before resetting the timezone
        if await ctx.ask("Are you sure you want to reset your timezone?"):
            # Reset the timezone of the author
            time_data.upsert(
                constraint='userid',
                userid=ctx.author.id,
                timezone=None
            )
            await ctx.reply("Your timezone has been reset.")
        else:
            await ctx.reply("Question cancelled. Your timezone has not been reset.")

    else:
        # All flags have been handled, all that remains is time reporting for targeted user or author.

        # Find the user
        if not ctx.guild:
            user = ctx.author
        else:
            user = (await ctx.find_member(ctx.args, interactive=True)) if ctx.args else ctx.author
        if user is None:
            # Failed to find the target user
            # find_member already complained, so just return
            return
        else:
            # Found a user, get their timezone and construct the time message
            tuser = time_data.select_where(userid=user.id)
            tz = tuser[0]['timezone'] if tuser else None

            if not tz:
                # Oops, this user doesn't have a timezone set.
                if user == ctx.author:
                    msg = ("You haven't set your timezone! "
                           "Set it using the interactive timezone picker with `{prefix}ti --set`.")
                elif ctx.guild and user == ctx.guild.me:
                    msg = random.choice(time_quotes)
                else:
                    msg = "This user hasn't set their timezone! Ask them to set it using `{prefix}ti --set`."
            else:
                timestr = get_timestr(tz, brief=brief)
                tdiffstr = await time_diff(ctx, tz, auth_tz, brief=brief) if user != ctx.author else ""
                msg = "The current time for **{}** is {}{}".format(user.name, timestr, tdiffstr or '.')
        await ctx.reply(msg.format(prefix=prefix))
