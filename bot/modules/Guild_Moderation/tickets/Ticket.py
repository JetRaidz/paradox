"""
ABC and data definitions for manual moderation tickets.
"""
from typing import Mapping
from typing import Any, List, Optional, Type, TypeVar
from datetime import datetime as dt

import discord

from cmdClient.cmdClient import cmdClient
from registry import tableInterface

from utils.lib import jumpto

from ..module import guild_moderation_module as module

from .TicketTypes import TicketType


T = TypeVar('T', bound='Ticket')


class Ticket:
    """
    Abstract base class represeting a moderation Ticket.

    Parameters
    ----------
    row: Mapping[str, Any]
        Table row as returned by `tableInterface.select_one_where`.
    memberids: list[int]
        List of memberids associated with the ticket.
    **kwargs:
        Extra instantiation parameters, handled by subclasses.

    Attributes
    ----------
    guildid: int
        ID of the guild which owns the ticket.
    modid: int
        ID of the moderator responsible for the ticket.
    agentid: int
        ID of the agent through which the ticket action was done.
        This will usually be the original moderator or a bot.
    memberids: list[int]
        List of members associated to the ticket.
    ticketid: int
        Global unique integer id for this ticket.
        Generated and retrieved from the database on ticket creation.
    guild_ticketid: int
        Guild-local id for this ticket.
        Derived by the database.
    created_at: int
        The utc timestamp of the original action or the ticket creation, depending on the ticket type.
    app: str
        Application which created this ticket.
        As tickets are shared between applications, this is completely internal.
    msgid: Optional[int]
        Message id of the ticket embed in the modlog.
    auditid: Optional[int]
        The id of the associated audit log entry, if any.
    reason: Optional[str]
        The reason associated with the action, if any.
    """
    __slots__ = (
        'guildid',
        'modid',
        'agentid',
        'memberids',
        'ticketid',
        'ticketgid',
        'created_at',
        'app',
        'msgid',
        'auditid',
        'reason',
    )
    _client: cmdClient = None  # Client, attached at initialisation

    # Data interfaces
    _ticket_data: tableInterface = None  # Ticket properties, interface for the raw ticket table
    _member_data: tableInterface = None  # Ticket members, interface for the ticket member table

    # Ticket properties with extra properties joined or derived from all ticket types
    _combined_ticket_data: tableInterface = None

    # Type of ticket the class represents
    _ticket_type = None

    def __init__(self, row: Mapping[str, Any], memberids: List[int], *args):
        self.guildid: int = row['guildid']
        self.modid: int = row['modid']
        self.agentid: int = row['agentid']
        self.ticketid: int = row['ticketid']
        self.ticketgid: int = row['ticketgid']
        self.app: str = row['app']
        self.msgid: int = row['msgid']
        self.auditid: int = row['auditid']
        self.reason: str = row['reason']
        self.created_at: int = row['created_at']

        self.memberids: List[int] = memberids

    @property
    def embed(self):
        """
        The ticket embed representing the ticket in the modlog.
        This is expected to be extended or overridden to display type-specific information.
        """
        # Base embed
        embed = discord.Embed(
            title="Ticket #{}".format(self.ticketgid),
            timestamp=dt.fromtimestamp(self.created_at)
        )

        # Moderator information
        mod_user = self._client.get_user(self.modid)
        if mod_user is not None:
            embed.set_footer(text="Responsible moderator: {}".format(mod_user), icon_url=mod_user.display_avatar)
        else:
            embed.set_footer(text="Responsible moderator: {}".format(self.modid))

        # Target information
        targets = '\n'.join("<@{0}> ({0})".format(targetid) for targetid in self.memberids)
        if len(self.memberids) == 1:
            embed.description = "`Target`: {}".format(targets)
        else:
            embed.add_field(name="Targets", value=targets, inline=False)

        # Reason
        if self.reason:
            embed.add_field(name='Reason', value=self.reason, inline=False)

        return embed

    @property
    def short_summary(self):
        """
        Brief one-line summary of the ticket.
        """
        return "**{}**".format(self._ticket_type.name)

    @property
    def field_summary(self):
        """
        Ticket summary as a tuple `(name, value)` suitable for an embed field.
        """
        name = "(#{}) **{}** on {} by {}".format(
            self.ticketgid,
            self._ticket_type.name,
            dt.fromtimestamp(self.created_at),
            self._client.get_user(self.modid) or self.modid
        )
        value = self.reason or "No reason given"
        return (name, value)

    @property
    def jumpto(self):
        """
        Link to jump to the ticket message in the modlog.
        """
        # Get the modlog
        modlogid = self._client.guild_config.modlog.get(self._client, self.guildid).data

        if modlogid and self.msgid:
            return jumpto(self.guildid, modlogid, self.msgid)

    @classmethod
    def setup(cls, client):
        cls._client = client
        cls._ticket_data: tableInterface = client.data.guild_mod_tickets  # type: tableInterface
        cls._member_data = client.data.guild_mod_ticket_members  # type: tableInterface
        cls._combined_ticket_data = client.data.guild_mod_tickets_combined  # type: tableInterface

    @classmethod
    def create(cls: Type[T], guildid: int, modid: int, agentid: int, memberids: List[int],
               auditid: Optional[int] = None, reason: Optional[str] = None, **kwargs) -> T:
        """
        Create a new ticket with the given parameters.
        Individual ticket types should extend this if they carry extra properties.
        Returns the created ticket.
        """
        if cls._ticket_type is None:
            raise ValueError("Cannot create a ticket without a ticket type.")

        # Save the ticket data
        curs = cls._ticket_data.insert(
            ticket_type=cls._ticket_type.value,
            app=cls._client.app,
            guildid=guildid,
            modid=modid,
            agentid=agentid,
            auditid=auditid,
            reason=reason,
            created_at=int(dt.utcnow().timestamp())
        )

        # Retrieve the ticket id
        ticketid = curs.lastrowid

        # Save the member data
        cls._member_data.insert_many(
            *((ticketid, memberid) for memberid in memberids),
            insert_keys=('ticketid', 'memberid')
        )

        return cls._create_ticket(ticketid, memberids, **kwargs)

    @classmethod
    def _create_ticket(cls, ticketid, memberids, **kwargs):
        # Retrieve, construct, and return the Ticket
        row = cls._combined_ticket_data.select_one_where(ticketid=ticketid)
        return cls(row, memberids)

    @classmethod
    def fetch_tickets_where(cls: Type[T], memberid=None, **kwargs) -> List[T]:
        """
        Fetch tickets matching the given criteria.
        Additionally filters by the current `_ticket_type`, if set and not given in `kwargs`.

        Parameters
        ----------
        memberid: Optional[int]
            Filter for tickets with the given memberid associated.
        **kwargs:
            Remaining kwargs must be valid columns of `_combined_ticket_data`.
            Their values will be transparently passed to `select_where()`.
        """
        tickets = []
        member_rows = []

        if memberid is not None:
            rows = cls._member_data.select_where(memberid=memberid)
            if not rows:
                return []

            ticketids = [row['ticketid'] for row in rows]

            given_ticketids = kwargs.pop('ticketid', None)
            if given_ticketids is None:
                kwargs['ticketid'] = ticketids
            elif isinstance(given_ticketids, (list, tuple)):
                kwargs['ticketid'] = list(set(given_ticketids).intersection(ticketids))
            elif given_ticketids in ticketids:
                kwargs['ticketid'] = given_ticketids
            else:
                return []

        if cls._ticket_type is not None and 'ticket_type' not in kwargs:
            kwargs['ticket_type'] = cls._ticket_type.value

        ticket_rows = cls._combined_ticket_data.select_where(**kwargs)
        if ticket_rows:
            ticketids = [row['ticketid'] for row in ticket_rows]
            member_rows = cls._member_data.select_where(ticketid=ticketids)

            ticket_members = {ticketid: [] for ticketid in ticketids}
            for row in member_rows:
                ticket_members[row['ticketid']].append(row['memberid'])

            for row in ticket_rows:
                tickets.append(
                    TicketType(row['ticket_type']).Ticket(row, ticket_members[row['ticketid']])
                )
        else:
            return []

        return tickets

    def update(self, **kwargs) -> T:
        """
        Updates and saves the ticket information using the provided kwargs.
        Subclasses should extend or override this if they require new data fields.
        """
        for attr, value in kwargs.items():
            setattr(self, attr, value)

        new_memberids = kwargs.pop('memberids', None)

        if kwargs:
            self._ticket_data.update_where(
                kwargs,
                ticketid=self.ticketid
            )

        if new_memberids is not None:
            self._member_data.delete_where(ticketid=self.ticketid)
            self._member_data.insertmany(
                ('ticketid', 'memberid'),
                *((self.ticketid, memberid) for memberid in new_memberids)
            )

        return self

    async def post(self):
        """
        Posts or updates the ticket embed in the modlog.
        If the modlog `msgid` doesn't exist or the message cannot be found/updated,
        posts a new ticket and saves the `msgid`.

        Fails silently with most error conditions (e.g. guild or modlog not found).
        """
        # Get the modlog
        modlog = self._client.guild_config.modlog.get(self._client, self.guildid).value

        if modlog is not None:
            message = None
            if self.msgid:
                # Get the message, if possible
                try:
                    message = await modlog.fetch_message(self.msgid)
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    return None
                except discord.HTTPException:
                    return None

                if message is not None and message.author != self._client.user:
                    # The message was probably sent by another app
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        pass
                    message = None

            if message is not None:
                # Edit the message
                await message.edit(embed=self.embed)
            else:
                # Post the message
                message = await modlog.send(embed=self.embed)

                # Save the message id
                self.update(msgid=message.id)


module.init_task(Ticket.setup)
