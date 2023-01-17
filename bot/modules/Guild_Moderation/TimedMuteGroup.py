from typing import List
import traceback
import logging
import asyncio
import datetime as dt

import discord

from cmdClient.cmdClient import cmdClient

from registry import tableInterface, Column, ColumnType, ForeignKey, ReferenceAction, tableSchema
from utils.lib import strfdelta

from .module import guild_moderation_module as module

from .tickets import TicketType
from .mute_utils import unmute_memberid


class TimedMuteGroup:
    __slots__ = (
        'ticket',
        'memberids',
        '_task',
        '_cancelled'
    )
    _client: cmdClient = None  # Attached during initialisation

    _member_data: tableInterface = None  # Attached during initialisation

    # Cache associating muted members to timed mute groups
    _member_map = {}  # type: Dict[int, Dict[int, TimedMuteGroup]]

    def __init__(self, timed_mute_ticket: TicketType.TEMPMUTE.Ticket, memberids: List[int]):
        self.ticket = timed_mute_ticket
        self.memberids = memberids

        self._task = None
        self._cancelled = False

    @property
    def guild_mutes(self):
        """
        The mute member cache associated to the current guild.
        Creates the cache if it doesn't exist.
        """
        cache = self._member_map.get(self.ticket.guildid, None)
        if cache is None:
            cache = self._member_map[self.ticket.guildid] = {}
        return cache

    # Client initialisation and launch methods
    @classmethod
    def setup(cls, client):
        """
        Initialisation task.
        Attaches the client, along with the guild and member data interfaces.
        Also adds the mute cache as a client object for external use.
        """
        cls._client = client  # type: cmdClient
        cls._member_data = client.data.guild_timed_mute_members  # type: tableInterface

    @classmethod
    async def launch(cls, client):
        """
        Launch task.
        Populate the caches and schedule the pending mutes.
        """
        client.log(
            "Populating timed mute cache.",
            context="LAUNCH_TIMED_MUTES"
        )
        # Collect the group members
        group_members = {}  # groupid: list_of_members
        for row in cls._member_data.select_where():
            if row['ticketid'] not in group_members:
                group_members[row['ticketid']] = []
            group_members[row['ticketid']].append(row['memberid'])

        # Build the tickets
        tickets = TicketType.TEMPMUTE.Ticket.fetch_tickets_where(
            app=client.app,
            ticketid=list(group_members.keys())
        ) if group_members else []

        # Build the groups
        group_counter = 0
        cleanup = []  # List of ticketids that are "stale" (e.g. non-existent guild or role), and should be removed
        for ticket in tickets:
            guild = client.get_guild(ticket.guildid)
            if guild is not None:
                mute_role = guild.get_role(ticket.roleid)
                if mute_role is not None:
                    cls(ticket, group_members[ticket.ticketid]).load()
                    group_counter += 1
                else:
                    cleanup.append(ticket.ticketid)
            else:
                cleanup.append(ticket.ticketid)

        # Log the loaded mute groups
        client.log(
            "Loaded and scheduled {} timed mute groups.".format(group_counter),
            context="LAUNCH_TIMED_MUTES"
        )

        # Handle cleanup if required
        if cleanup:
            client.log(
                "Cleaning up stale timed mute groups.",
                context="LAUNCH_TIMED_MUTES"
            )
            cls._member_data.delete_where(ticketid=cleanup)
            client.log(
                "Successfully cleaned up {} stale timed mute groups.".format(len(cleanup)),
                context="LAUNCH_TIMED_MUTES"
            )

    # Activation and deactivation of the TimedMuteGroup
    def load(self):
        """
        Initial activation of a TimedMuteGroup.
        Removes group members from any other TimedMuteGroups, populates the cache, and schedules the unmute task.
        Returns `self` for easy chaining.
        """
        # Add members to the guild cache, and remove them from any existing mute groups
        for memberid in self.memberids:
            if memberid in self.guild_mutes:
                self.guild_mutes[memberid].remove(memberid)
            self.guild_mutes[memberid] = self

        self._schedule()
        return self

    def unload(self):
        """
        Removes the TimedMuteGroup from the cache and cancels the unmute task.
        """
        self._cancel()

        # Remove the mute from cache, if it still exists
        for memberid in self.memberids:
            self.guild_mutes.pop(memberid, None)

    def destroy(self):
        """
        Unloads the TimedMuteGroup and deletes it from data.
        """
        self.unload()
        self._member_data.delete_where(ticketid=self.ticket.ticketid)

    # Application interface and member management
    def remove(self, *memberids):
        """
        Remove a sequence of users from the mute group.
        If there are no users left, unloads the group and cancels the unmute task.
        """
        # Remove from internal mute group list
        self.memberids = [memberid for memberid in self.memberids if memberid not in memberids]

        # Remove from guild cache
        [self.guild_mutes.pop(memberid, None) for memberid in memberids]

        # Remove from data
        self._member_data.delete_where(ticketid=self.ticket.ticketid, memberid=memberids)

        # Close and cancel if there are no users left
        if not self.memberids:
            self.unload()

    # Internal creation and cancellation of the mute task
    def _schedule(self):
        """
        Create and schedule the unmute task for this group.
        """
        # Create the group unmute task as self._task
        self._task = asyncio.create_task(self._unmute_wrapper())

    def _cancel(self):
        """
        Cancel the unmute task, if it is running.
        """
        if not self._cancelled and self._task and not self._task.done():
            self._task.cancel()
            self._cancelled = True

    # Internal unmute system
    async def _unmute_wrapper(self):
        """
        Unmute wrapper which runs `apply_unmutes` at `self.ticket.unmute_timestamp`.
        """
        try:
            # Sleep for the required time
            await asyncio.sleep(self.ticket.unmute_timestamp - dt.datetime.utcnow().timestamp())

            # Execute the unmutes
            await self._unmute_members()
            if self._cancelled:
                # Wait a moment to catch the cancel, in case it was propogated from inside the unmute
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Unknown exception!
            full_traceback = traceback.format_exc()

            self._client.log(
                ("Caught an unknown exception during schedule unmute with groupid {groupid}."
                 "{traceback}").format(
                     groupid=self.ticket.ticketid,
                     traceback='\n'.join('\t' + line for line in full_traceback.splitlines()),
                 ),
                context="tid:{}".format(self.ticket.ticketid),
                level=logging.ERROR)

            raise e

    async def _unmute_members(self):
        """
        Attempt to apply the unmutes.
        Posts to the modlog with a summary if possible.
        Closes the TimedUnmute if there are no users left in the group.
        """
        guild: discord.Guild = self._client.get_guild(self.ticket.guildid)
        if guild is not None:
            role: discord.Role = guild.get_role(self.ticket.roleid)
            if role is not None:
                await asyncio.gather(
                    *(unmute_memberid(memberid,
                                      role,
                                      audit_reason="Automatic unmute (#{}).".format(self.ticket.ticketgid))
                      for memberid in self.memberids)
                )
                reason = (
                    "Automatic unmute after {}.\n"
                    "[Click here for the original mute ticket]({})"
                ).format(
                    strfdelta(dt.timedelta(seconds=self.ticket.duration)),
                    self.ticket.jumpto
                )
                await TicketType.UNMUTE.Ticket.create(
                    self.ticket.guildid, self.ticket.modid, self._client.user.id, self.memberids,
                    reason=reason
                ).post()

        # Delete the group
        self.destroy()


module.init_task(TimedMuteGroup.setup)
module.launch_task(TimedMuteGroup.launch)

member_schema = tableSchema(
    "guild_timed_mute_members",
    Column('ticketid', ColumnType.INT, primary=True, required=True),
    Column('memberid', ColumnType.SNOWFLAKE, primary=True, required=True),
    ForeignKey('ticketid', 'guild_moderation_tickets', 'ticketid', on_delete=ReferenceAction.CASCADE)
)


@module.data_init_task
def attach_timed_mute_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, member_schema, shared=True),
        "guild_timed_mute_members"
    )
