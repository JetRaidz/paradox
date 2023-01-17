import discord
import string

from wards import guild_moderator
from cmdClient import Context
from .module import guild_admin_module as module


@module.cmd("rmrole",
            desc="Deletes the provided role",
            aliases=["removerole", "remrole", "deleterole", "delrole"])
@guild_moderator()
async def cmd_rmrole(ctx: Context):
    """
    Usage``:
        {prefix}rmrole <rolename>
    Description:
        Deletes a role given by partial name or mention.
    """
    if not ctx.arg_str:
        return await ctx.error_reply("Please provide a role to delete.")
    role = await ctx.find_role(ctx.arg_str, create=False, interactive=True)
    if not role:
        return
    # Various checks to avoid hard errors and prevent abuse.
    if role.managed:
        return await ctx.error_reply("Roles managed by an integration cannot be deleted.")
    if (role > ctx.author.top_role) and (ctx.guild.owner != ctx.author):
        return await ctx.error_reply("You cannot delete a role above you in the role hierarchy.")
    if role > ctx.guild.me.top_role:
        return await ctx.error_reply("I cannot delete a role above me in the role hierarchy.")
    if not ctx.guild.me.guild_permissions.manage_roles:
        return await ctx.error_reply("I lack the permissions to delete the role.")
    if role == ctx.guild.default_role:
        return await ctx.error_reply("The default role cannot be deleted.")
    try:
        await role.delete(reason=f"Moderator: {ctx.author}")
    except Exception:
        return await ctx.error_reply("An unknown error occurred while attempting to delete the role. Please try again.")
    await ctx.reply("Successfully deleted the role.")


@module.cmd("editrole",
            desc="Create or edit a server role.",
            aliases=["erole", "roleedit", "roledit", "editr"],
            flags=["colour=", "color=", "name==", "perm==", "hoist=", "mention=", "pos=="])
@guild_moderator()
async def cmd_editrole(ctx: Context, flags):
    """
    Usage``:
        {prefix}editrole <rolename> [flags]
    Description:
        Modifies the specified role, either interactively (WIP), or using the provided flags (see below).
        This may also be used to create a role.
    Flags::
        colour:  Change the colour of the role (input: hex code)
        name: Change the name of the role
        perm: Add or remove a permission (WIP)
        hoist: Hoist or unhoist the role (input: "yes"/"no")
        mention: Toggle the ability for everybody to mention this role (input: "yes"/"no")
        pos: Modify the role's hierarchy. (input: number | up | down | above <role> | below <role>)
    Examples:
        {prefix}erole Member --colour #0047AB --name Noob
        {prefix}erole Regular --pos above Member
    """
    if not ctx.arg_str:
        return await ctx.error_reply("Please provide a role to edit.")

    params = ctx.args.split(maxsplit=1)
    role = await ctx.find_role(params[0], create=True, interactive=True)
    if not role:
        return
    edits = {}
    if role >= ctx.guild.me.top_role:
        return await ctx.error_reply("I can't edit a role equal to or above my top role.")

    if not ctx.guild.me.guild_permissions.manage_roles:
        return await ctx.error_reply("I require the permission `Manage Roles` to run this command.")

    if flags["colour"] or flags["color"]:
        colour = flags["colour"] if flags["colour"] else flags["color"]
        hexstr = colour.strip("#")
        if not (len(hexstr) == 6 or all(c in string.hexdigits for c in hexstr)):
            return await ctx.error_reply("Please provide a valid hex colour (e.g. #0047AB).")
        edits["colour"] = discord.Colour(int(hexstr, 16))

    if flags["name"]:
        edits["name"] = flags["name"]

    if flags["perm"]:
        return await ctx.reply("Sorry, perm modification is a work in progress. Please check back later!")

    if flags["hoist"]:
        if flags["hoist"].lower() in ["enable", "yes", "on"]:
            hoist = True
        elif flags["hoist"].lower() in ["disable", "no", "off"]:
            hoist = False
        else:
            return await ctx.error_reply("An invalid argument was passed to `--hoist`. Use `help editrole` for usage.")
        edits["hoist"] = hoist

    if flags["mention"]:
        if flags["mention"].lower() in ["enable", "yes", "on"]:
            mention = True
        elif flags["mention"].lower() in ["disable", "no", "off"]:
            mention = False
        else:
            return await ctx.error_reply("An invalid argument was passed to `--mention`. Use `help editrole` for usage.")
        edits["mentionable"] = mention

    position = None
    if flags["pos"]:
        pos_flag = flags["pos"]
        if pos_flag.isdigit():
            position = int(pos_flag)
        elif pos_flag.lower() == "up":
            position = role.position + 1
        elif pos_flag.lower() == "down":
            position = role.position - 1
        elif pos_flag.startswith("above"):
            target_role = await ctx.find_role((' '.join(pos_flag.split(' ')[1:])).strip(), create=False, interactive=True)
            position = target_role.position + 1
        elif pos_flag.startswith("below"):
            target_role = await ctx.find_role((' '.join(pos_flag.split(' ')[1:])).strip(), create=False, interactive=True)
            position = target_role.position
        else:
            return await ctx.error_reply("An invalid argument was passed to `--pos`. Use `help editrole` for usage.")

    if position is not None:
        if position > ctx.guild.me.top_role.position:
            return await ctx.error_reply("The target position is higher than my top role.")
        if position == 0:
            return await ctx.error_reply("The role can't be below the default server role.")
        try:
            await role.edit(position=position)
        except discord.Forbidden:
            return await ctx.error_reply("I lack the permissions to edit the role.")
        except discord.HTTPException:
            return await ctx.error_reply("An unknown error occurred while trying to modify the role position.")
    if edits:
        try:
            await role.edit(**edits, reason=f"Moderator: {ctx.author}")
        except discord.Forbidden:
            return await ctx.error_reply("I don't have enough permissions to make the specified edits.")

    if not (flags["colour"] or flags["color"] or flags["name"] or flags["perm"] or flags["hoist"] or flags["mention"] or flags["pos"]):
        return await ctx.reply("Interactive role editing is a work in progress, please check back later!")
    await ctx.reply("The role was modified successfully.")
