import asyncio
import datetime as dt

import discord

from cmdClient.lib import SafeCancellation

from wards import guild_moderator, chunk_guild

from .module import guild_moderation_module as module

from . import mute_config  # noqa

from .tickets import TicketType
from .TimedMuteGroup import TimedMuteGroup
from .ModAction import ModAction, ActionState
from .mute_utils import mute_member, unmute_member


class _MuteTypeAction(ModAction):
    def __init__(self, ctx, flags):
        super().__init__(ctx, flags)

        self.duration = None
        self.mute_role = None

    async def run(self):
        self.mute_role = await self.fetch_muterole()
        await super().run()

    async def fetch_muterole(self):
        # Get the muterole
        muterole = self.ctx.get_guild_setting.muterole.value
        if not muterole or not isinstance(muterole, discord.Role):
            raise SafeCancellation(
                "Please setup the muterole (`{}config muterole`) "
                "before using mute commands.".format(self.ctx.best_prefix())
            )

        # Check the client has sufficient permissions to manage it
        manager_role = max(
            (role for role in self.ctx.guild.me.roles
             if role.permissions.manage_roles or role.permissions.administrator),
            default=None
        )
        if not manager_role or manager_role <= muterole:
            raise SafeCancellation(
                "Insufficient permissions to manage the mute role!"
            )

        return muterole


class MuteAction(_MuteTypeAction):
    resp_seeker_timed_out = "Member selection timed out, no members were muted."
    resp_seeker_cancelled = "Member selection cancelled, no members were muted."
    resp_reason_timed_out = "Reason prompt timed out, no members were muted."
    resp_reason_cancelled = "Reason prompt cancelled, no members were muted."
    reason_prompt = "Please enter a reason for this mute, or `c` to cancel."

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Muted",
        ActionState.MEMBER_NOTFOUND: "Couldn't find the member to mute them!",
        ActionState.IAM_FORBIDDEN: "I don't have permissions to apply the mute role!",
        ActionState.YOUARE_FORBIDDEN: "You don't have permissions to mute this member!"
    }

    single_success_report = "Muted {target.mention}."
    single_failure_report = "Failed to mute {target.mention}: {state}"
    summary_success_report = "Muted {count} members."
    summary_failure_report = "Failed to mute {count} members."

    async def action(self):
        """
        Mute action.
        Mutes the given targets and creates a Mute ticket or TimedMuteTicket as required.
        In the case of a Timed mute, also creates and loads a TimedMuteGroup.
        """
        ctx = self.ctx

        # Mute targets and gather results
        audit_reason = "Muted by {}: {}".format(self.ctx.author.id, self.short_reason)
        results = await asyncio.gather(
            *(mute_member(target, self.mute_role, audit_reason=audit_reason) for target in self.targets)
        )
        member_results = dict(zip(self.targets, results))
        successful = [member.id for member, result in member_results.items() if result is ActionState.SUCCESS]

        if successful:
            # Remove members from any timed mute group
            if self.ctx.guild.id in TimedMuteGroup._member_map:
                guild_mutes = TimedMuteGroup._member_map[self.ctx.guild.id]
                for memberid in successful:
                    if memberid in guild_mutes:
                        guild_mutes[memberid].remove(memberid)

            # Create and post mute ticket
            ticket = TicketType.MUTE.Ticket.create(
                ctx.guild.id, ctx.author.id, ctx.client.user.id,
                successful, reason=self.reason
            )
            await ticket.post()
            self.ticket = ticket

        return member_results


class TimedMuteAction(_MuteTypeAction):
    resp_seeker_timed_out = "Member selection timed out, no members were muted."
    resp_seeker_cancelled = "Member selection cancelled, no members were muted."
    resp_reason_timed_out = "Reason prompt timed out, no members were muted."
    resp_reason_cancelled = "Reason prompt cancelled, no members were muted."
    reason_prompt = "Please enter a reason for this mute, or `c` to cancel."

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Muted",
        ActionState.MEMBER_NOTFOUND: "Couldn't find the member!",
        ActionState.IAM_FORBIDDEN: "I don't have permissions to apply the mute role!",
        ActionState.YOUARE_FORBIDDEN: "You don't have permissions to mute this member!"
    }

    single_success_report = "Muted {target.mention} for {self.duration_str}."
    single_failure_report = "Failed to mute {target.mention}: {state}"
    summary_success_report = "Muted {count} members for {self.duration_str}."
    summary_failure_report = "Failed to mute {count} members."

    async def action(self):
        """
        Mute action.
        Mutes the given targets and creates a Mute ticket or TimedMuteTicket as required.
        In the case of a Timed mute, also creates and loads a TimedMuteGroup.
        """
        ctx = self.ctx

        # Mute targets and gather results
        audit_reason = "Muted by {}: {}".format(self.ctx.author.id, self.short_reason)
        results = await asyncio.gather(
            *(mute_member(target, self.mute_role, audit_reason=audit_reason) for target in self.targets)
        )
        member_results = dict(zip(self.targets, results))
        successful = [member.id for member, result in member_results.items() if result is ActionState.SUCCESS]

        if successful:
            # Temporary mute

            # Collect mute data
            unmute_at = int(dt.datetime.utcnow().timestamp() + self.duration)

            # Create and post ticket
            ticket = TicketType.TEMPMUTE.Ticket.create(
                ctx.guild.id, ctx.author.id, ctx.client.user.id,
                successful, reason=self.reason, duration=self.duration, roleid=self.mute_role.id,
                unmute_timestamp=unmute_at
            )
            await ticket.post()

            # Create and load timed mute group
            TimedMuteGroup(ticket, successful).load()
            self.ticket = ticket

        return member_results


class UnMuteAction(_MuteTypeAction):
    resp_seeker_timed_out = "Member selection timed out, no members were unmuted."
    resp_seeker_cancelled = "Member selection cancelled, no members were unmuted."
    resp_reason_timed_out = "Reason prompt timed out, no members were unmuted."
    resp_reason_cancelled = "Reason prompt cancelled, no members were unmuted."
    reason_prompt = "Please enter a reason for this unmute, or `c` to cancel."

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Unmuted",
        ActionState.MEMBER_NOTFOUND: "Couldn't find the member to unmute them!",
        ActionState.IAM_FORBIDDEN: "I don't have permissions to remove the mute role!",
        ActionState.YOUARE_FORBIDDEN: "You don't have permissions to unmute this member!"
    }

    single_success_report = "Unmuted {target.mention}."
    single_failure_report = "Failed to unmute {target.mention}: {state}"
    summary_success_report = "Unmuted {count} members."
    summary_failure_report = "Failed to unmute {count} members."

    async def action(self):
        """
        Unmute action.
        Unmutes the given targets and creates an Unmute ticket.
        """
        ctx = self.ctx

        # Mute targets and gather results
        audit_reason = "Unmuted by {}: {}".format(self.ctx.author.id, self.short_reason)
        results = await asyncio.gather(
            *(unmute_member(target, self.mute_role, audit_reason=audit_reason) for target in self.targets)
        )
        member_results = dict(zip(self.targets, results))
        successful = [member.id for member, result in member_results.items() if result is ActionState.SUCCESS]

        if successful:
            # Remove members from any timed mute group
            if self.ctx.guild.id in TimedMuteGroup._member_map:
                guild_mutes = TimedMuteGroup._member_map[self.ctx.guild.id]
                for memberid in successful:
                    if memberid in guild_mutes:
                        guild_mutes[memberid].remove(memberid)

            # Create and post unmute ticket
            ticket = TicketType.UNMUTE.Ticket.create(
                ctx.guild.id, ctx.author.id, ctx.client.user.id,
                successful, reason=self.reason
            )
            await ticket.post()
            self.ticket = ticket

        return member_results


# TODO: Muterole creation
@module.cmd("mute",
            desc="Silence a misbehaving user for a specified amount of time.",
            flags=['r==', 'f', 't=='],
            handle_edits=False)
@guild_moderator()
@chunk_guild()
async def cmd_mute(ctx, flags):
    """
    Usage``:
        {prefix}mute user1, user2, user3, ... [-r <reason>] [-t <duration>]
    Description:
        Mutes the listed users with an optional reason.

        To use this command, you need to be a **guild moderator**.\
            That is, you need to have the `manage_guild` permission or the configured `modrole`.
        This command also requires that the `muterole` is\
            configured at `{prefix}config muterole`.
    Flags::
        ​r: (reason) Provide a reason for the mute (avoids the reason prompt).
        ​t: (time) Provide a duration for the mute, e.g. `1h 10m`.
    Examples``:
        {prefix}mute {ctx.author} -t 1d
    """
    await (TimedMuteAction(ctx, flags).run() if isinstance(flags['t'], str) else MuteAction(ctx, flags).run())


@module.cmd("unmute",
            desc="Unmute muted users.",
            flags=['r==', 'f'],
            handle_edits=False)
@guild_moderator()
@chunk_guild()
async def cmd_unmute(ctx, flags):
    """
    Usage``:
        {prefix}unmute user1, user2, user3, ... [-r <reason>]
    Description:
        Unmutes the listed users with an optional reason.

        To use this command, you need to be a **guild moderator**.\
            That is, you need to have the `manage_guild` permission or the configured `modrole`.
        This command also requires that the `muterole` is\
            configured at `{prefix}config muterole`.
    Flags::
        ​r: (reason) Provide a reason for the unmute.
    Examples``:
        {prefix}unmute {ctx.author}
    """
    await UnMuteAction(ctx, flags).run()
