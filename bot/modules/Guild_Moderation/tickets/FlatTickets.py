from . import Ticket, describes_ticket, TicketType


flat_tickets = [
    (TicketType.MUTE, 'Mute'),
    (TicketType.UNMUTE, 'Unmute'),
    (TicketType.BAN, 'Ban'),
    (TicketType.UNBAN, 'Unban'),
    (TicketType.PREBAN, 'Preban'),
    (TicketType.KICK, 'Kick'),
]

for ttype, name in flat_tickets:
    @describes_ticket(ttype)
    class _FlatTicket(Ticket):
        @property
        def embed(self):
            embed = super().embed
            embed.set_author(name=self._ticket_name)
            return embed
    _FlatTicket._ticket_name = name
