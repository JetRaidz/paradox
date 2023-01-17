import re
import asyncio
import discord

from cmdClient.lib import SafeCancellation
from wards import chunk_guild

from .module import guild_moderation_module as module

from .tickets import TicketType
from .ModAction import ModAction, ActionState


class HammerAction(ModAction):
    """
    General Hammer action base.
    """
    Ticket = None
    required_permissions: discord.Permissions = None
    lack_permissions_resp: str = "You don't have the required permissions to do this!"

    def __init__(self, ctx, flags):
        super().__init__(ctx, flags)

        self.mod = ctx.author
        # Highest role with the required permissions, or None if the moderator is the guild owner
        self.modrole = None

    async def run(self, **kwargs):
        self.modrole = await self.fetch_modrole()
        await super().run(**kwargs)

    async def fetch_modrole(self):
        """
        Returns the highest role the moderator has with the required permissions.
        Throws `SafeCancellation` if they do not have sufficient permissions.
        May return `None` if the moderator is the server owner.
        """
        if self.mod.id == self.ctx.guild.owner_id:
            return None

        # Fetch highest manager role
        manager_role = max(
            (role for role in self.mod.roles
             if role.permissions.administrator or self.required_permissions.is_subset(role.permissions)),
            default=None
        )
        guild_modrole = self.ctx.get_guild_setting.modrole.value
        modrole = guild_modrole if guild_modrole in self.mod.roles else None

        if manager_role and modrole:
            modrole = max((manager_role, modrole))
        else:
            modrole = manager_role or modrole
        if not modrole:
            raise SafeCancellation(
                self.lack_permissions_resp.format(self=self)
            )

        return modrole

    async def action(self, **kwargs):
        ctx = self.ctx

        # Mute targets and gather results
        results = await asyncio.gather(
            *(self._single_target_action(target, **kwargs) for target in self.targets)
        )
        member_results = dict(zip(self.targets, results))
        successful = [member.id for member, result in member_results.items() if result is ActionState.SUCCESS]

        if successful:
            # Create and post ticket
            ticket = self.Ticket.create(
                ctx.guild.id, ctx.author.id, ctx.client.user.id, successful, reason=self.reason
            )
            await ticket.post()
            self.ticket = ticket

        return member_results

    async def _single_target_action(self, target: discord.Member, **kwargs) -> ActionState:
        raise NotImplementedError


class BanAction(HammerAction):
    resp_seeker_timed_out = "Member selection timed out, no members were banned."
    resp_seeker_cancelled = "Member selection cancelled, no members were banned."
    resp_reason_timed_out = "Reason prompt timed out, no members were banned."
    resp_reason_cancelled = "Reason prompt cancelled, no members were banned."
    reason_prompt = "Please enter a reason for the ban, or `c` to cancel."

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Banned",
        ActionState.MEMBER_NOTFOUND: "Couldn't find the member to ban them!",
        ActionState.IAM_FORBIDDEN: "I don't have permissions to ban this member!",
        ActionState.YOUARE_FORBIDDEN: "You don't have permissions to ban this member!"
    }

    single_success_report = "Banned {target.mention} and purged {days} days of history."
    single_failure_report = "Failed to ban {target.mention}: {state}"
    summary_success_report = "Banned {count} members and purged {days} days of history."
    summary_failure_report = "Failed to ban {count} members."

    Ticket = TicketType.BAN.Ticket
    required_permissions: discord.Permissions = discord.Permissions(ban_members=True)
    lack_permissions_resp: str = "You don't have the required permissions to ban members here!"
    audit_reason = "Banned by {self.mod.id}: {self.short_reason}"

    async def _single_target_action(self, target: discord.Member, days=0, **kwargs):
        if self.modrole is not None and self.modrole <= target.top_role:
            return ActionState.YOUARE_FORBIDDEN

        try:
            await target.ban(reason=self.audit_reason.format(self=self), delete_message_days=days)
        except discord.Forbidden:
            return ActionState.IAM_FORBIDDEN
        except discord.HTTPException:
            return ActionState.INTERNAL_UNKNOWN
        else:
            return ActionState.SUCCESS


@module.cmd("ban",
            desc="Permanently remove a misbehaving user from the guild.",
            flags=['r==', 'p='],
            aliases=["bean"])
@chunk_guild()
async def cmd_ban(ctx, flags):
    """
    Usage``:
        {prefix}ban user1, user2, user3, ... [-r <reason>] [-p <days>]
    Description:
        Bans the listed users with an optional reason.

        To use this command, you need to be able to ban members manually, or have the configured `modrole`.
    Flags::
        ​r: (reason) Provide a reason for the ban (avoids the reason prompt).
        ​p: (purge) Number of days of messages to purge (defaults to 1).
    """
    await BanAction(ctx, flags).run(days=int(flags['p']) if isinstance(flags['p'], str) else 1)


class UnbanAction(HammerAction):
    resp_seeker_timed_out = "User selection timed out, no users were unbanned."
    resp_seeker_cancelled = "User selection cancelled, no users were unbanned."
    resp_reason_timed_out = "Reason prompt timed out, no users were unbanned."
    resp_reason_cancelled = "Reason prompt cancelled, no users were unbanned."
    reason_prompt = "Please enter a reason for the unban, or `c` to cancel."

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Unbanned",
        ActionState.MEMBER_NOTFOUND: "Couldn't find the user to unban them!",
        ActionState.IAM_FORBIDDEN: "I don't have permissions to unban!",
        ActionState.YOUARE_FORBIDDEN: "You don't have permissions to unban!"
    }

    target_not_found_error = "Couldn't find a banned user matching `{targetstr}`!"

    single_success_report = "Unbanned {target}."
    single_failure_report = "Failed to unban {target}: {state}"
    summary_success_report = "Unbanned {count} users."
    summary_failure_report = "Failed to unban {count} users."

    Ticket = TicketType.UNBAN.Ticket
    required_permissions: discord.Permissions = discord.Permissions(ban_members=True)
    lack_permissions_resp: str = "You don't have the required permissions to unban users here!"
    audit_reason = "Unbanned by {self.mod.id}: {self.short_reason}"

    async def get_collection(self):
        bans = []

        # No limit may be slow for large guilds, default is 1000
        async for ban in self.ctx.guild.bans(limit=None):
            bans.append(ban.user)

        return bans

    async def _single_target_action(self, target: discord.User, **kwargs):
        try:
            await self.ctx.guild.unban(target, reason=self.audit_reason.format(self=self))
        except discord.Forbidden:
            return ActionState.IAM_FORBIDDEN
        except discord.HTTPException:
            return ActionState.INTERNAL_UNKNOWN
        else:
            return ActionState.SUCCESS


@module.cmd("unban",
            desc="Unban a previously banned user.",
            flags=['r=='])
@chunk_guild()
async def cmd_unban(ctx, flags):

    """
    Usage``:
        {prefix}unban user1, user2, user3, ... [-r <reason>]
    Description:
        Unbans the listed users with an optional reason.

        To use this command, you need to be able to unban users manually, or have the configured `modrole`.
    Flags::
        ​r: (reason) Provide a reason for the unban (avoids the reason prompt).
    """
    await UnbanAction(ctx, flags).run()


class KickAction(HammerAction):
    resp_seeker_timed_out = "Member selection timed out, no members were kicked."
    resp_seeker_cancelled = "Member selection cancelled, no members were kicked."
    resp_reason_timed_out = "Reason prompt timed out, no members were kicked."
    resp_reason_cancelled = "Reason prompt cancelled, no members were kicked."
    reason_prompt = "Please enter a reason for the kick, or `c` to cancel."

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Kicked",
        ActionState.MEMBER_NOTFOUND: "Couldn't find the member to kick them!",
        ActionState.IAM_FORBIDDEN: "I don't have permissions to kick this member!",
        ActionState.YOUARE_FORBIDDEN: "You don't have permissions to kick this member!"
    }

    single_success_report = "Kicked {target}."
    single_failure_report = "Failed to kick {target}: {state}"
    summary_success_report = "Kicked {count} users."
    summary_failure_report = "Failed to kick {count} users."

    Ticket = TicketType.KICK.Ticket
    required_permissions: discord.Permissions = discord.Permissions(kick_members=True)
    lack_permissions_resp: str = "You don't have the required permissions to kick members here!"
    audit_reason = "Kicked by {self.mod.id}: {self.short_reason}"

    async def _single_target_action(self, target: discord.User, **kwargs):
        if self.modrole is not None and self.modrole <= target.top_role:
            return ActionState.YOUARE_FORBIDDEN

        try:
            await self.ctx.guild.kick(target, reason=self.audit_reason.format(self=self))
        except discord.Forbidden:
            return ActionState.IAM_FORBIDDEN
        except discord.HTTPException:
            return ActionState.INTERNAL_UNKNOWN
        else:
            return ActionState.SUCCESS


@module.cmd("kick",
            desc="Kick a user from the guild.",
            flags=['r=='])
@chunk_guild()
async def cmd_kick(ctx, flags):
    """
    Usage``:
        {prefix}kick user1, user2, user3, ... [-r <reason>]
    Description:
        Kicks the listed users with an optional reason.

        To use this command, you need to be able to kick users manually, or have the configured `modrole`.
    Flags::
        ​r: (reason) Provide a reason for the kick (avoids the reason prompt).
    """
    await KickAction(ctx, flags).run()


class PreBanAction(HammerAction):
    resp_reason_timed_out = "Reason prompt timed out, no users were banned."
    resp_reason_cancelled = "Reason prompt cancelled, no users were banned."
    reason_prompt = "Please enter a reason for the preban, or `c` to cancel."

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Prebanned",
        ActionState.MEMBER_NOTFOUND: "Couldn't find the user to preban them!",
        ActionState.IAM_FORBIDDEN: "I don't have permissions to ban this user!",
        ActionState.YOUARE_FORBIDDEN: "You don't have permissions to ban this user!"
    }

    single_success_report = "Prebanned {target}."
    single_failure_report = "Failed to preban {target}: {state}"
    summary_success_report = "Prebanned {count} users."
    summary_failure_report = "Failed to preban {count} users."

    Ticket = TicketType.PREBAN.Ticket
    required_permissions: discord.Permissions = discord.Permissions(ban_members=True)
    lack_permissions_resp: str = "You don't have the required permissions to ban users here!"
    audit_reason = "Pre-banned by {self.mod.id}: {self.short_reason}"

    async def identify_targets(self):
        targets = []
        user_strs = re.split(',|\n', self.ctx.args)
        if len(user_strs) > 20:
            raise SafeCancellation("Please provide less than 20 users at once!")
        if not all(user_str.isdigit() for user_str in user_strs):
            raise SafeCancellation(
                "Please provide preban targets via user id."
            )
        for user_str in user_strs:
            userid = int(user_str)
            user = self.ctx.client.get_user(userid)
            if user is None:
                try:
                    user = await self.ctx.client.fetch_user(userid)
                except discord.NotFound:
                    raise SafeCancellation("Couldn't find any users with id `{}`".format(user_str))
            targets.append(user)
        return targets

    async def _single_target_action(self, target: discord.User, **kwargs):
        try:
            await self.ctx.guild.ban(target, reason=self.audit_reason.format(self=self))
        except discord.Forbidden:
            return ActionState.IAM_FORBIDDEN
        except discord.HTTPException:
            return ActionState.INTERNAL_UNKNOWN
        else:
            return ActionState.SUCCESS


@module.cmd("preban",
            desc="Preemptively ban users from the guild by user id.",
            flags=['r=='])
@chunk_guild() # Does preban need chunking?
async def cmd_preban(ctx, flags):
    """
    Usage``:
        {prefix}preban userid1, userid2, userid3, ... [-r <reason>]
    Description:
        Bans the listed users with an optional reason.
        This command may be applied to users who are not in the guild, but all targets must be given by their id.

        To use this command, you need to be able to ban users manually, or have the configured `modrole`.
    Flags::
        ​r: (reason) Provide a reason for the preban (avoids the reason prompt).
    """
    await PreBanAction(ctx, flags).run()
