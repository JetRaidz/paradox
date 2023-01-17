import datetime as dt

from registry import tableInterface, Column, ColumnType, tableSchema, ForeignKey, ReferenceAction

from utils.lib import strfdelta

from ..module import guild_moderation_module as module
from . import Ticket, describes_ticket, TicketType
from . import ticket_data  # noqa


@describes_ticket(TicketType.TEMPMUTE)
class TimedMuteTicket(Ticket):
    __slots__ = (
        'duration',
        'roleid',
        'unmute_timestamp'
    )

    def __init__(self, row, memberids):
        super().__init__(row, memberids)
        self.duration = row['tmute_duration']
        self.roleid = row['tmute_roleid']
        self.unmute_timestamp = row['tmute_unmute_timestamp']

    @property
    def embed(self):
        embed = super().embed
        embed.set_author(name="Timed Mute")
        desc = embed.description or ""
        desc += "\nMuted for {}".format(strfdelta(dt.timedelta(seconds=self.duration)))
        embed.description = desc
        return embed

    @classmethod
    def _create_ticket(cls, ticketid, memberids, duration=None, roleid=None, unmute_timestamp=None):
        # Save the extra timed mute data
        cls._client.data.guild_timed_mute_tickets.insert(
            ticketid=ticketid,
            duration=duration,
            roleid=roleid,
            unmute_timestamp=unmute_timestamp
        )

        # Finish creating the ticket
        return super()._create_ticket(ticketid, memberids)


schema = tableSchema(
    "guild_timed_mute_tickets",
    Column('ticketid', ColumnType.INT, required=True),
    Column('duration', ColumnType.INT, required=True),
    Column('roleid', ColumnType.SNOWFLAKE, required=True),
    Column('unmute_timestamp', ColumnType.INT, required=True),
    ForeignKey('ticketid', 'guild_moderation_tickets', 'ticketid', on_delete=ReferenceAction.CASCADE)
)


@module.data_init_task
def attach_mute_ticket_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=True),
        "guild_timed_mute_tickets"
    )
