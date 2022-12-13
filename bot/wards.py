import logging
import discord
import asyncio

from cmdClient import check
from config import get_conf


@check(name="ALWAYS_FAIL",
       msg="This operation is impossible!")
async def fail_ward(ctx, *args, **kwargs):
    return False


@check(name="IS_MASTER",
       msg="You must be a bot owner to use this command!")
async def is_master(ctx, *args, **kwargs):
    return ctx.author.id in get_conf().getintlist("masters", [])


@check(name="IS_DEV",
       msg="You must be a bot developer to use this command!",
       parents=[is_master])
async def is_dev(ctx, *args, **kwargs):
    return ctx.author.id in get_conf().getintlist("developers", [])


@check(name="IS_MANAGER",
       msg="You must be a bot manager to use this command!",
       parents=[is_dev])
async def is_manager(ctx, *args, **kwargs):
    return ctx.author.id in get_conf().getintlist("managers", [])


@check(name="IS_REVIEWER",
       msg="You must be a preamble reviewer to use this command!",
       parents=[is_manager])
async def is_reviewer(ctx, *args, **kwargs):
    return ctx.author.id in get_conf().getintlist("reviewers", [])


@check(name="IN_GUILD",
       msg="This command may only be used in a guild.")
async def in_guild(ctx, *args, **kwargs):
    return bool(ctx.msg.guild)


@check(name="GUILD_MODERATOR",
       msg="This may only be done by a moderator!",
       requires=[in_guild])
async def guild_moderator(ctx, *args, **kwargs):
    has_mod = ctx.author.guild_permissions.administrator
    has_mod = has_mod or ctx.author.guild_permissions.manage_guild

    modrole = ctx.get_guild_setting.modrole.value
    has_mod = has_mod or (modrole and modrole in ctx.author.roles)
    return has_mod


@check(name="GUILD_MANAGER",
       msg="You need the `manage guild` permission to do this!",
       requires=[in_guild])
async def guild_manager(ctx, *args, **kwargs):
    return ctx.author.guild_permissions.manage_guild


@check(name="GUILD_ADMIN",
       msg="You need the `administrator` permission to do this!",
       requires=[in_guild])
async def guild_admin(ctx, *args, **kwargs):
    return ctx.author.guild_permissions.administrator


@check(name="CHUNK_GUILD",
       msg=None,
       requires=[in_guild])
async def chunk_guild(ctx, *args, **kwargs):

    progress_msg = "Loading your guild, please wait..."
    progress_msg_large = "Loading your guild, please wait...\nDue to the size of the guild, this may take a few seconds."

    # The guild isn't chunked, begin
    if not ctx.guild.chunked:

        # Gracefully error if the bot lacks the Members Privileged Intent
        if not ctx.client.intents.members:
            ctx.log(f"Failed to chunk guild {ctx.guild.name} ({ctx.guild.id}) as the bot lacks Members Privileged Intent.",
                    level=logging.ERROR)
            await ctx.reply("Failed to load your guild. The bot requires the Members Privileged Intent for this to function.")
            return False

        task = asyncio.create_task(ctx.guild.chunk())
        ctx.log(f"Command {ctx.cmd.name} requested guild chunking for {ctx.guild.name} ({ctx.guild.id}).",
                level=logging.WARNING)

        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=1)
            # The guild has been chunked successfully!
            ctx.log(f"{ctx.guild.name} ({ctx.guild.id}) is now chunked.")

        # Chunking the guild is taking longer than normal, send a message to the author
        except asyncio.TimeoutError:

            # If the guild has over 20000 members, send a message warning them about extra time
            if ctx.guild.member_count > 20000:
                msg = progress_msg_large
            else:
                msg = progress_msg
            progress = await ctx.reply(msg)

            try:
                await asyncio.wait_for(task, timeout=10)

            # It has taken 10 seconds and there has been no response
            # Either Discord isn't working or the request was left hanging
            except asyncio.TimeoutError:
                client.log(f"Timed out chunking guild {guild.name} ({guild.id}).",
                           level=logging.WARNING)
                progress = await progress.edit(content="Failed to load your guild. Please try again in a few minutes.")
                return False

            else:
                # The guild has successfully been chunked but took longer than normal
                ctx.log(f"{ctx.guild.name} ({ctx.guild.id}) is now chunked.")
                progress = await progress.edit(content="Your guild has been loaded successfully.")
                progress = await progress.delete()
                return True

    # The guild is already chunked, skip the chunking process
    return True



# Old wards, not migrated
# async def perm_manage_server(ctx):
#     if (ctx.user is None) or (ctx.server is None):
#         return (2, "An internal error occurred.")
#     if not (ctx.user.server_permissions.manage_server or
#             ctx.user.server_permissions.administrator):
#         return (1, "You lack the `Manage Server` permission on this server!")
#     return (0, "")


# async def perm_ban_members(ctx):
#     if (ctx.user is None) or (ctx.server is None):
#         return (2, "An internal error occurred.")
#     if not (ctx.user.server_permissions.ban_members or
#             ctx.user.server_permissions.administrator):
#         return (1, "You lack the `Ban Members` permission on this server!")
#     return (0, "")

# async def perm_kick_members(ctx):
#     if (ctx.user is None) or (ctx.server is None):
#         return (2, "An internal error occurred.")
#     if not (ctx.user.server_permissions.kick_members or
#             ctx.user.server_permissions.administrator):
#         return (1, "You lack the `Kick Members` permission on this server!")
#     return (0, "")

# # Mod action checks

# async def check_in_server_has_mod(ctx):
#     if (ctx.user is None) or (ctx.server is None):
#         return (2, "An internal error occurred.")
#     (code, msg) = await checks["has_manage_server"](ctx)
#     if code == 0:
#         return (code, msg)
#     mod_role = await ctx.server_conf.mod_role.get(ctx)
#     if mod_role:
#         mod_role = discord.utils.get(ctx.server.roles, id=mod_role)
#     if not mod_role:
#         (code, msg) = await checks["has_manage_server"](ctx)
#         return (code, msg)
#     if mod_role in ctx.member.roles:
#         return (0, "")
#     else:
#         return (1, "You don't have the moderator role in this server!")

# async def check_in_server_can_ban(ctx):
#     """
#     TODO: Need to do proper custom checks here
#     """
#     (code, msg) = await checks["in_server_has_mod"](ctx)
#     if code == 0:
#         return (code, msg)
#     (code, msg) = await checks["has_ban_members"](ctx)
#     if code == 0:
#         return (code, msg)
#     else:
#         return (1, "You don't have permission to ban users in this server!")
#     return (0, "")

# async def check_in_server_can_unban(ctx):
#     """
#     TODO: Need to do proper custom checks here
#     """
#     (code, msg) = await checks["in_server_has_mod"](ctx)
#     if code == 0:
#         return (code, msg)
#     (code, msg) = await checks["has_ban_members"](ctx)
#     if code == 0:
#         return (code, msg)
#     else:
#         return (1, "You don't have permission to unban users in this server!")
#     return (0, "")

# async def check_in_server_can_ban(ctx):
#     """
#     TODO: Need to do proper custom checks here
#     """
#     (code, msg) = await checks["in_server_has_mod"](ctx)
#     if code == 0:
#         return (code, msg)
#     (code, msg) = await checks["has_ban_members"](ctx)
#     if code == 0:
#         return (code, msg)
#     else:
#         return (1, "You don't have permission to hackban users in this server!")
#     return (0, "")

# async def check_in_server_can_kick(ctx):
#     """
#     TODO: Need to do proper custom checks here
#     """
#     (code, msg) = await checks["in_server_has_mod"](ctx)
#     if code == 0:
#         return (code, msg)
#     (code, msg) = await checks["has_kick_members"](ctx)
#     if code == 0:
#         return (code, msg)
#     else:
#         return (1, "You don't have permission to kick users in this server!")
#     return (0, "")


# async def check_in_server_can_softban(ctx):
#     """
#     TODO: Need to do proper custom checks here
#     """
#     (code, msg) = await checks["in_server_has_mod"](ctx)
#     if code == 0:
#         return (code, msg)
#     (code, msg) = await checks["has_ban_members"](ctx)
#     if code == 0:
#         return (code, msg)
#     else:
#         return (1, "You don't have permission to softban users in this server!")
#     return (0, "")

# async def check_in_server_can_softban(ctx):
#     """
#     TODO: Need to do proper custom checks here
#     """
#     (code, msg) = await checks["in_server_has_mod"](ctx)
#     if code == 0:
#         return (code, msg)
#     else:
#         return (1, "You don't have permission to mute users in this server!")
#     return (0, "")

# async def check_in_server_can_softban(ctx):
#     """
#     TODO: Need to do proper custom checks here
#     """
#     (code, msg) = await checks["in_server_has_mod"](ctx)
#     if code == 0:
#         return (code, msg)
#     else:
#         return (1, "You don't have permission to unmute users in this server!")
#     return (0, "")
