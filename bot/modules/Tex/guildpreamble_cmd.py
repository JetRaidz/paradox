from cmdClient.lib import ResponseTimedOut

from utils.lib import substitute_ranges
from wards import in_guild, guild_admin

from .module import latex_module as module

from .core.LatexGuild import LatexGuild
from .core.preamble_utils import preamblelog, view_preamble, confirm
from .resources import default_preamble


@module.cmd("guildpreamble",
            desc="View or modify the guild's default LaTeX preamble",
            aliases=['serverpreamble', 'gpreamble'],
            flags=['reset', 'add', 'remove', 'replace'])
@in_guild()
async def cmd_gpreamble(ctx, flags):
    """
    Usage``:
        {prefix}gpreamble
        {prefix}gpreamble [--replace] [code]
        {prefix}gpreamble --reset
        {prefix}gpreamble --add [code]
        {prefix}gpreamble --remove [code]
    Description:
        View or modify the *guild's* custom preamble.
        This preamble is used as a default for members without a custom personal preamble.

        Similar to `preamble`, this command accepts an uploaded text file as `code`.
        Unlike `preamble`, the default action is *replacing* rather than *appending*.

        It is recommended to store, test, and edit the guild preamble locally.
        **Improper use of this command may render LaTeX unusuable in the guild.**

        Modifications to the guild preamble require the `Administrator` permission.
    Flags::
        replace: Replaces the guild preamble with the provided `code`.
        reset: Resets the guild preamble.
        add: Append `code` to the guild preamble.
        remove: Remove all lines from the guild preamble containing `code`,
        or prompt for specific line numbers to remove.
    Related:
        preamble, config, texconfig
    """
    lguild = LatexGuild.get(ctx.guild.id)
    guild_preamble = lguild.preamble
    guild_preamble_data = ctx.client.data.guild_latex_preambles

    # Actual current resolved preamble
    preamble = guild_preamble or default_preamble

    # Human readable guild information for logging headers
    log_str = "{} ({})".format(ctx.guild.name, ctx.guild.id)

    # Handle resetting the preamble
    if flags["reset"]:
        if not await guild_admin.run(ctx):
            return await ctx.error_reply("You need the `Administrator` permission to reset the guild preamble!")

        # Handle not having a preamble
        if not guild_preamble:
            return await ctx.error_reply("No guild preamble set, nothing to reset!")

        # Ask the user if they are sure, handling timeout and negative response
        try:
            resp = await ctx.ask(
                "Are you sure you want to reset the guild preamble? "
                "This is not reversible!",
                timeout=60
            )
        except ResponseTimedOut:
            return await ctx.error_reply(
                "Timed out waiting for a response, the guild preamble was not modified."
            )
        if not resp:
            return await ctx.error_reply("Cancelling preamble reset, the guild preamble was not modified.")

        # Now reset the preamble
        guild_preamble_data.delete_where(guildid=ctx.guild.id)
        lguild.load()

        # Logging
        await preamblelog(ctx, "Guild preamble has been reset.", author=log_str)

        return await ctx.reply("The guild preamble was reset.")

    # Get any input, including the contents of any attached files if they exist
    if ctx.msg.attachments:
        attachment = ctx.msg.attachments[0]

        # If the file is over 1MB, it probably isn't a valid preamble.
        if attachment.size >= 1000000:
            return await ctx.error_reply("Attached file is too large to process (over `1MB`).")

        try:
            args = str(await attachment.read(), encoding='utf-8', errors="strict")
        except UnicodeError:
            return await ctx.error_reply(
                "Couldn't decode the attached file, please ensure it uses the `utf-8` codec."
            )
    else:
        args = ctx.args
    args = args.strip()

    # Handle a request to remove material from the preamble
    if flags['remove']:
        if not await guild_admin.run(ctx):
            return await ctx.error_reply("You need the `Administrator` permission to modify the guild preamble!")

        to_remove = []  # List of line indicies to remove
        new_preamble = None
        lines = preamble.splitlines()

        # If arguments were given, search the current preamble for this string
        if args:
            if args not in preamble:
                return await ctx.error_reply(
                    "The requested text doesn't appear in the guild preamble! Nothing to remove."
                )
            if '\n' in args:
                # If the requested string has multiple lines and appears, just remove all of them
                new_preamble = preamble.replace(args, "")
            else:
                # Otherwise, make a list of matching lines to remove
                to_remove = [i for i, line in enumerate(lines) if args in line]
        else:
            # If we aren't given anything to remove, prompt the user for which lines they want to remove
            # Generate a version of the current preamble with line numbers
            lined_preamble = "\n".join(("{:>2}. {}".format(i+1, line) for i, line in enumerate(lines)))

            # Show this to the user and prompt them
            prompt = ("Please enter the line numbers and ranges to remove, "
                      "separated by commas, or type `c` now to cancel.\n"
                      "(Example input: `1, 2-5, 10-20`)")
            prompt_msg = await view_preamble(ctx, lined_preamble, prompt)

            # Handle timeouts and negative response
            try:
                response = await ctx.input(prompt_msg)
            except ResponseTimedOut:
                return await ctx.error_reply("Prompt timed out. The guild preamble was not modified.")
            if response.lower() == "c":
                return await ctx.error_reply("Preamble modification cancelled. The guild preamble was not updated.")

            # Parse provided selection
            parse_failure = False

            # First sanity check input
            if not all((char.isdigit() or not char.strip() or char in ('-', ',')) for char in response):
                parse_failure = True

            # Replace ranges
            try:
                response = substitute_ranges(response)
            except ValueError:
                parse_failure = True

            # Extract numbers
            nums = [num.strip() for num in response.split(',')]
            if not all(num.isdigit() for num in nums):
                parse_failure = True

            # Handle unspecified parsing failure along the way
            if parse_failure:
                return await ctx.error_reply(
                    "Couldn't parse your selection!\n"
                    "Please enter numbers and ranges of numbers separated by commas, e.g. "
                    "`1, 2-5, 10-20`."
                )

            # Calculate line indicies
            nums = [int(num) - 1 for num in nums]
            if not all(0 <= num < len(lines) for num in nums):
                return await ctx.error_reply(
                    "Couldn't remove requested lines, your selection goes outside of the guild preamble!"
                )

            # Remove duplicates and set the list of line indices to remove
            to_remove = list(set(nums))

        # Prompt the user and remove the requested lines
        if to_remove:
            for_removal = "\n".join([lines[i] for i in to_remove])
            prompt = "Are you sure you want to remove the following lines from the guild preamble?"
            try:
                result = await confirm(ctx, prompt, for_removal)
            except ResponseTimedOut:
                return await ctx.error_reply("Prompt timed out, the guild preamble was not modified.")
            if not result:
                return await ctx.error_reply("Cancelled preamble modification, the guild preamble was not modified.")

            new_preamble = "\n".join([line for i, line in enumerate(lines) if i not in to_remove])

        # Finally save the new preamble
        if new_preamble is not None:
            guild_preamble_data.insert(
                allow_replace=True,
                guildid=ctx.guild.id,
                preamble=new_preamble
            )
            lguild.load()
            await ctx.reply("The guild preamble has been updated.")
            await preamblelog(
                ctx,
                "Material was removed from the preamble. New preamble below.",
                author=log_str,
                source=new_preamble
            )
        return

    # Handle a request to add material to the preamble
    if flags['add']:
        if not await guild_admin.run(ctx):
            return await ctx.error_reply("You need the `Administrator` permission to modify the guild preamble!")

        if not args:
            # Prompt the user for the material they wish to add, handle cancellations and timeout
            prompt = (
                "Please enter the material you wish to add to the guild preamble, or send `c` to cancel.\n"
                "**If you wish to *replace* the guild preamble, please rerun with `{}preamble --replace`.**\n"
            ).format(ctx.best_prefix())
            try:
                args = await ctx.input(prompt, timeout=600)
            except ResponseTimedOut:
                return await ctx.error_reply("Query timed out, the guild preamble was not modified.")
            if args.lower() == 'c':
                return await ctx.error_reply("Query cancelled, the guild preamble was not modified.")

        new_submission = "{}\n{}".format(preamble, args)

        # Set various warnings
        nonmatching_brackets = False
        duplicate_packages = False
        many_duplicates = False

        new_lines = new_submission.splitlines()

        duplicate_count = 0
        unique_lines = set()
        for line in new_lines:
            if len(line) > 5:
                if line in unique_lines:
                    duplicate_count += 1
                    if not duplicate_packages and line.strip().startswith('\\usepackage'):
                        duplicate_packages = True
                else:
                    unique_lines.add(line)
        many_duplicates = (duplicate_count > 10)
        nonmatching_brackets = not(
            (new_submission.count('(') == new_submission.count(')')) and
            (new_submission.count('{') == new_submission.count('}'))
        )
        warnings = []
        if nonmatching_brackets:
            warnings.append("Number of opening and closing brackets and parenthesis do not match!")
        if duplicate_packages:
            warnings.append("Duplicate package imports detected!")
        if many_duplicates:
            warnings.append("Many duplicate lines detected in submission!")
        warnings = "\n".join(warnings)

        # Confirm submission
        prompt = "Please confirm that you want to set the following updated guild preamble."
        try:
            result = await confirm(
                ctx,
                prompt,
                new_submission,
                start_page=-1,
                extra_fields=[("Warnings", warnings)] if warnings else None
            )
        except ResponseTimedOut:
            return await ctx.error_reply("Prompt timed out, the guild preamble was not modified.")
        if not result:
            return await ctx.error_reply("Preamble extension cancelled, the guild preamble was not modified.")

        # Finally save the new preamble
        if new_submission is not None:
            guild_preamble_data.insert(
                allow_replace=True,
                guildid=ctx.guild.id,
                preamble=new_submission
            )
            lguild.load()
            await ctx.reply("The guild preamble has been updated.")
            await preamblelog(
                ctx,
                "Material was added to the guild preamble. New preamble below.",
                author=log_str,
                source=new_submission
            )
        return

    # Handle a request to replace the preamble
    if flags['replace'] or args:
        if not await guild_admin.run(ctx):
            return await ctx.error_reply("You need the `Administrator` permission to modify the guild preamble!")

        if not args:
            # Prompt the user for the new preamble, handle cancellations and timeout
            prompt = ("Please enter the new guild preamble, or `c` to cancel.\n"
                      "If you wish to upload the guild preamble as a file, "
                      "cancel now and rerun with the file attached.")
            try:
                new_submission = await ctx.input(prompt, timeout=600)
            except ResponseTimedOut:
                return await ctx.error_reply("Query timed out, the guild preamble was not modified.")
            if new_submission.lower() == 'c':
                return await ctx.error_reply("Preamble replacement cancelled, the guild preamble was not modified.")
        else:
            new_submission = args

        # Confirm submission
        prompt = "Please confirm the new guild preamble."
        try:
            result = await confirm(ctx, prompt, new_submission)
        except ResponseTimedOut:
            return await ctx.error_reply("Prompt timed out, the guild preamble was not modified.")
        if not result:
            return await ctx.error_reply("Preamble replacement cancelled, the guild preamble was not modified.")

        # Finally save the new preamble
        if new_submission is not None:
            guild_preamble_data.insert(
                allow_replace=True,
                guildid=ctx.guild.id,
                preamble=new_submission
            )
            lguild.load()
            await ctx.reply("The guild preamble has been updated.")
            await preamblelog(
                ctx,
                "The guild preamble was replaced. New preamble below.",
                author=log_str,
                source=new_submission
            )
        return

    # View the preamble
    if not guild_preamble:
        await ctx.reply("No guild default preamble set. Users without a custom preamble will use the global default.")
    else:
        await view_preamble(ctx, guild_preamble, "Current Guild Preamble")
