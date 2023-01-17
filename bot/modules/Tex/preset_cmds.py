@cmds.cmd("preamblepreset",
          category="Maths",
          short_help="Set your LaTeX preamble to a pre-built preset",
          aliases=["ppr"])
@cmds.execute("flags", flags=["use", "add", "remove", "show", 'modify'])
async def cmd_ppr(ctx):
    """
    Usage:
        {prefix}ppr
        {prefix}ppr --use [preset]
        {prefix}ppr --show [preset]
    Description:
        Set your LaTeX preamble to one of our pre-built preamble presets.
        If you wish to submit a new preset, please contact a bot manager on the support server!

        Use of a preamble preset doesn't require bot manager approval.
        Warning: This will completely overwrite your current preamble.
    Flags:4
        use:: Overwrites your LaTeX preamble with the selected preset.
        show:: View the selected preset, or list the available presets.
    Examples:
        {prefix}ppr --use
        {prefix}ppr --show funandgames
        {prefix}ppr --use physics
    """
    args = ctx.arg_str

    # Preset administration

    # Handle adding a new preset
    if ctx.flags['add']:
        # Check for managerial permissions
        (code, msg) = await cmds.checks["manager_perm"](ctx)
        if code != 0:
            return

        # Retrieve the name of the new preset
        name = args.strip()

        # If the name wasn't given, ask for it politely
        if not name:
            result = await ctx.input("Please enter a name for the preset.")
            if not result:
                return
            name = result.strip()

        # Now we have a name, ask for the source
        prompt = "Please enter or upload the new preset, or type `c` now to cancel."

        preset = None
        offer_msg = await ctx.reply(prompt)
        result_msg = await ctx.bot.wait_for_message(author=ctx.author, timeout=600)

        # Grab response content, using the contents of the first attachment if it exists
        if result_msg is None or result_msg.content.lower() in ["c", "cancel"]:
            pass
        else:
            preset = result_msg.content
            if not preset:
                if result_msg.attachments:
                    file_info = result_msg.attachments[0]

                    # Limit filesize to 16k
                    if file_info['size'] >= 16000:
                        await ctx.reply("Attached file is too large to process.")
                        return

                    async with aiohttp.get(file_info['url']) as r:
                        preset = await r.text()

        # Remove the prompt and response messages
        try:
            await ctx.bot.delete_message(offer_msg)
            if result_msg is not None:
                await ctx.bot.delete_message(result_msg)
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass

        # If out of all that we didn't get any content, return
        if not preset:
            return

        # Confirm submission
        prompt = "Please confirm the contents of the new preset {}.".format(name)
        result = await confirm(ctx, prompt, preset)

        if result is None:
            await ctx.reply("Query timed out, aborting.")
            return
        if not result:
            await ctx.reply("User cancelled, aborting.")
            return

        # Write the preset to a file
        file_name = os.path.join(preset_dir, name + '.tex')
        with open(file_name, 'w') as f:
            f.write(preset)

        # Add the preset name to the local cache
        presets.append(name)

        # Tell the manager that all is done
        await ctx.reply("Your new preset has been created!")
        return

    # Handle removing a preset
    if ctx.flags['remove']:
        # Check for managerial permissions
        (code, msg) = await cmds.checks["manager_perm"](ctx)
        if code != 0:
            return

        # Retrieve the name of the preset to remove
        name = args.strip()

        # If the name wasn't given, go through an interactive selection process
        # If it was given, ensure it is a valid preset
        if not name:
            # Selection header message
            message = "Please select a preamble preset to remove!"

            # Run the selector
            result = await ctx.selector(message, presets, allow_single=True)

            # Catch non-reply or cancellation
            if result is None:
                return

            name = presets[result]
        else:
            name = get_preset(name.strip())
            if not name:
                await ctx.reply("This preamble preset doesn't exist!")
                return

        # Confirm removal of the preset
        resp = await ctx.ask("Are you sure you wish to remove the preamble preset {}?".format(name))
        if resp:
            # Delete the preset from the file system
            file_name = os.path.join(preset_dir, name + '.tex')
            os.remove(file_name)

            # Remove the preset from local cache
            presets.remove(name)
            await ctx.reply("The preset has been deleted!")
        else:
            await ctx.reply("Aborting...")
        return

    # Handle modification of a preset
    if ctx.flags['modify']:
        """
        This displays a menu with three options:
            1. Add to preset
            2. Remove from preset
            3. Replace preset
        Add to and remove work as in the user's preamble system. Replace overwrites the preset.
        """
        # Check for managerial permissions
        (code, msg) = await cmds.checks["manager_perm"](ctx)
        if code != 0:
            return

        # Retrieve the name of the preset to remove
        name = args.strip()

        # If the name wasn't given, go through an interactive selection process
        # If it was given, ensure it is a valid preset
        if not name:
            # Selection header message
            message = "Please select a preamble preset to modify!"

            # Run the selector
            result = await ctx.selector(message, presets, allow_single=True)

            # Catch non-reply or cancellation
            if result is None:
                return

            name = presets[result]
        else:
            name = get_preset(name)
            if not name:
                await ctx.reply("This preamble preset doesn't exist!")
                return

        # Get the actual contents of the preset
        preset_file = os.path.join(preset_dir, name + '.tex')
        with open(preset_file, 'r') as f:
            preset = f.read()

        # Build menu
        menu_items = ["Add to preset", "Remove from preset", "Replace preset"]
        menu_message = "Please select the desired modification"

        # Run the selector
        result = await ctx.selector(menu_message, menu_items)
        if result is None:
            # Menu was cancelled or timed out
            return
        elif result == 0:
            # Adding lines to the preset
            resp = await ctx.input("Please enter the material you wish to add to the preset", timeout=600)
            if not resp:
                await ctx.reply("Query timed out, aborting.")
                return
            if resp.lower() == 'c':
                await ctx.reply("User cancelled, aborting.")
                return

            new_preset = "{}\n{}".format(preset, resp)
        elif result == 1:
            # Remove lines from the preset

            # Generate a lined version of the preset
            lines = preset.splitlines()
            lined_preset = "\n".join(("{:>2}. {}".format(i+1, line) for i, line in enumerate(lines)))

            # Prompt for the lines to remove
            prompt = "Please enter the line numbers to remove, separated by commas, or type `c` now to cancel."
            prompt_msg = await view_preamble(ctx, lined_preset, prompt)
            response = await ctx.input(prompt_msg=prompt_msg)
            if response is None:
                await ctx.reply("Query timed out, aborting.")
                return
            if response.lower() == "c":
                await ctx.reply("User cancelled, aborting.")
                return
            nums = [num.strip() for num in response.split(',')]
            if not all(num.isdigit() for num in nums):
                await ctx.reply("Couldn't understand your selection, aborting.")
                return
            nums = [int(num) - 1 for num in nums]
            if not all(0 <= num < len(lines) for num in nums):
                await ctx.reply("This line doesn't exist! Aborting.")
                return

            to_remove = list(set(nums))
            new_preset = "\n".join([line for i, line in enumerate(lines) if i not in to_remove])
        elif result == 2:
            # Completely replace preamble preset
            prompt = "Please enter or upload the new preset, or type `c` now to cancel."

            preset = None
            offer_msg = await ctx.reply(prompt)
            result_msg = await ctx.bot.wait_for_message(author=ctx.author, timeout=600)

            # Grab response content, using the contents of the first attachment if it exists
            if result_msg is None or result_msg.content.lower() in ["c", "cancel"]:
                pass
            else:
                new_preset = result_msg.content
                if not new_preset:
                    if result_msg.attachments:
                        file_info = result_msg.attachments[0]

                        # Limit filesize to 16k
                        if file_info['size'] >= 16000:
                            await ctx.reply("Attached file is too large to process.")
                            return

                        async with aiohttp.get(file_info['url']) as r:
                            preset = await r.text()

            # Remove the prompt and response messages
            try:
                await ctx.bot.delete_message(offer_msg)
                if result_msg is not None:
                    await ctx.bot.delete_message(result_msg)
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass

        if new_preset:
            # Confirm new content
            prompt = "Please confirm the following update for the preset {}".format(name)
            result = await confirm(ctx, prompt, new_preset)
            if result is None:
                await ctx.reply("Query timed out, aborting.")
                return
            if not result:
                await ctx.reply("User cancelled, aborting.")
                return

            # Update the preset
            file_name = os.path.join(preset_dir, name + '.tex')
            with open(file_name, 'w') as f:
                f.write(new_preset)

            # Notify the manager
            await ctx.reply("The preset has been updated!")
        return

    # End of manager level preset administration
    # Whether we are applying or showing the presets
    showing = not ctx.flags['use']  # We always want to show unless the use flag has been applied

    if not args:
        # Run through an interactive selection process

        # Selection header message
        message = "Please select a preamble preset to {}!".format('view' if showing else 'apply')

        # Run the selector
        result = await ctx.selector(message, presets, allow_single=True)

        # Catch non-reply or cancellation
        if result is None:
            return

        selected = presets[result]  # Name of the preset selected by the user
    else:
        # Check that the preset name entered with the command is a valid preset
        # If it is, set selected to this
        selected = get_preset(args.strip())

        if not selected:
            await ctx.reply("This isn't a valid preset! Use {}ppr --show to see the current list of presets!".format(ctx.used_prefix))
            return

    # selected now contains the name of a preset
    # Grab the actual preset from the preset directory
    preset_file = os.path.join(preset_dir, selected + '.tex')
    with open(preset_file, 'r') as f:
        preset = f.read()

    if showing:
        # View the preamble preset, with paging and a sendfile reaction
        title = "Preamble preset {}".format(selected)
        await view_preamble(ctx, preset, title, file_react=True)
    else:
        # Confirm that the user wishes to overwrite their current preamble with the preset
        prompt = "Are you sure you want to overwrite your current LaTeX preamble with the following preset?"
        result = await confirm(ctx, prompt, preset)

        # Handle empty results
        if result is None:
            await ctx.reply("Query timed out, aborting.")
            return
        if not result:
            await ctx.reply("User cancelled, aborting.")
            return

        # Set the preamble
        current_preamble = await ctx.data.users_long.get(ctx.authid, 'latex_preamble')
        await ctx.data.users_long.set(ctx.authid, 'previous_preamble', current_preamble)
        await ctx.data.users_long.set(ctx.authid, 'latex_preamble', preset)

        await ctx.reply("The preset has been applied!\
                        \nTo revert to your previous preamble, use `{}preamble --revert`".format(ctx.used_prefix))
        await preamblelog(ctx, "Preamble preset {} was applied".format(selected))
