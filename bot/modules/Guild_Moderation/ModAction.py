import re
import asyncio
import datetime
from enum import Enum

import discord

from cmdClient import Context
from cmdClient.lib import ResponseTimedOut, UserCancelled, SafeCancellation

from utils.lib import strfdelta, parse_dur


class ActionState(Enum):
    """
    Final state of a moderation action.
    """
    INTERNAL_UNKNOWN = -1  # Unknown internal error occurred
    SUCCESS = 0  # Successfully completed the action
    MEMBER_NOTFOUND = 1  # Couldn't find the member
    IAM_FORBIDDEN = 2  # I have insufficient permissions
    YOUARE_FORBIDDEN = 3  # Moderator has insufficient permissions


# TODO: Custom seeker error handling, member not found and no members in collection
class ModAction:
    resp_seeker_timed_out = "Member selection timed out."
    resp_seeker_cancelled = "Member selection cancelled."
    resp_reason_timed_out = "Reason prompt timed out."
    resp_reason_cancelled = "Reason prompt cancelled."
    reason_prompt = "Please enter a reason, or `c` to cancel."

    target_not_found_error = "Couldn't find a member matching `{targetstr}`!"

    state_response_map = {
        ActionState.INTERNAL_UNKNOWN: "An unknown error occurred!",
        ActionState.SUCCESS: "Acted",
        ActionState.MEMBER_NOTFOUND: "Could not find member",
        ActionState.IAM_FORBIDDEN: "I do not have the permissions to do this",
        ActionState.YOUARE_FORBIDDEN: "You do not have the permissions to do this"
    }

    single_success_report = "Acted on {target}."
    single_failure_report = "Failed to act on {target}: {state}"
    summary_success_report = "Acted on {count} members."
    summary_failure_report = "Failed to act on {count} members."

    def __init__(self, ctx: Context, flags):
        self.ctx: Context = ctx
        self.flags = flags

        self.reason = None
        self.targets = None
        self.ticket = None
        self.duration = None

    @property
    def duration_str(self):
        if self.duration is None:
            raise ValueError("No duration to stringify!")
        return strfdelta(datetime.timedelta(seconds=self.duration))

    @property
    def short_reason(self):
        """
        Shortened version of the reason, limited to 470 characters.
        Useful for adding a reason to the audit log.
        """
        return self.reason if len(self.reason) < 470 else self.reason[:467] + '...'

    async def get_collection(self):
        """
        Collection of users to lookup targets in.
        Override to specify a custom collection.
        """
        return None

    async def run(self, **kwargs):
        """
        Execute the operation.
        """
        await self.parse_args()
        results = await self.action(**kwargs)
        await self.report(results, **kwargs)

    async def parse_args(self):
        """
        Extract operation arguments from context.
        """
        # Handle no arguments
        if not self.ctx.args:
            await self.ctx.reply(embed=self.ctx.usage_embed())
            raise SafeCancellation()

        # Identify targets
        self.targets = await self.identify_targets()

        # Obtain reason
        self.reason = await self.request_reason()

        # Obtain duration, if required
        if 't' in self.flags and isinstance(self.flags['t'], str):
            self.duration = parse_dur(self.flags['t'])
            if self.duration > 365 * 24 * 60 * 60:
                raise SafeCancellation("Maximum duration is 1 year!")

    async def action(self, **kwargs):
        """
        Action to complete once arguments have been parsed.
        This includes creation of the action ticket.

        Returns: Dict[member, ActionState]
            A mapping associating each member to the action state.
        """
        raise NotImplementedError

    async def report(self, results, **kwargs):
        """
        Report based on the results of the action.
        """
        if len(self.targets) == 1:
            target = self.targets[0]
            result = results[target]

            if result == ActionState.SUCCESS:
                description = "[Ticket #{ticket.ticketgid}]({ticket.jumpto}): {template}".format(
                    ticket=self.ticket,
                    template=self.single_success_report.format(self=self, target=target, **kwargs)
                )
            else:
                description = self.single_failure_report.format(
                    self=self, target=target, state=self.state_response_map[result], **kwargs
                )
            await self.ctx.reply(embed=discord.Embed(description=description))
        else:
            targets_failed = [target for target, result in results.items() if result is not ActionState.SUCCESS]

            summary_components = []
            if len(targets_failed) != len(results):
                summary_components.append(
                    "[Ticket #{ticket.ticketgid}]({ticket.jumpto}):".format(ticket=self.ticket)
                )
                summary_components.append(
                    self.summary_success_report.format(self=self,
                                                       count=len(results) - len(targets_failed),
                                                       **kwargs)
                )
            if targets_failed:
                summary_components.append(
                    self.summary_failure_report.format(self=self,
                                                       count=len(targets_failed),
                                                       **kwargs)
                )
            summary = ' '.join(summary_components)

            target_lines = [
                "{emoji} {target}: {state}".format(
                    emoji=("✅" if result is ActionState.SUCCESS else "❌"),
                    target=target,
                    state=self.state_response_map[result]
                ) for target, result in results.items()
            ]
            target_line_blocks = ['\n'.join(target_lines[i:i+10]) for i in range(0, len(target_lines), 10)]
            embeds = [
                discord.Embed(
                    description="{}```{}```".format(summary, block)
                ).set_footer(
                    text="Page {}/{}".format(n+1, len(target_line_blocks))
                )
                for n, block in enumerate(target_line_blocks)
            ]
            await self.ctx.pager(embeds)

    async def identify_targets(self):
        targets = []
        user_strs = re.split(',|\n', self.ctx.args)
        if len(user_strs) > 20:
            raise SafeCancellation("Please provide less than 20 users at once!")
        for user_str in user_strs:
            try:
                member = await self.ctx.find_member(
                    user_str.strip(),
                    interactive=True,
                    collection=await self.get_collection(),
                    silent_notfound=True
                )
            except ResponseTimedOut:
                raise ResponseTimedOut(self.resp_seeker_timed_out) from None
            except UserCancelled:
                raise UserCancelled(self.resp_seeker_cancelled) from None
            if member is None:
                # No matches for this member
                raise SafeCancellation(
                    self.target_not_found_error.format(targetstr=user_str, self=self)
                )
            targets.append(member)
        return targets

    async def request_reason(self):
        # Interactively request the reason
        try:
            if isinstance(self.flags['r'], str):
                reason = self.flags['r']
                interactive = False
            else:
                reason = await self.ctx.input(self.reason_prompt)
                interactive = True
        except ResponseTimedOut:
            raise ResponseTimedOut(self.resp_reason_timed_out) from None
        if reason.lower() == 'c':
            raise UserCancelled(self.resp_reason_cancelled)
        if len(reason) > 1000:
            msg = "For display reasons, the reason must be under 1000 characters!"
            if interactive:
                msg = await self.ctx.reply(
                    msg,
                    embed=discord.Embed(title="Provided reason", description=reason, colour=discord.Color.orange())
                )
                asyncio.create_task(self.ctx.offer_delete(msg))
            else:
                await self.ctx.error_reply(msg)
            raise SafeCancellation()
        return reason
