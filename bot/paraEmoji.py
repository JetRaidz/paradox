from discord import PartialEmoji


class configEmoji(PartialEmoji):
    __slots__ = PartialEmoji.__slots__ + ('fallback',)

    def __init__(self, *args, fallback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fallback = fallback

    @classmethod
    def from_str(cls, emojistr: str):
        """
        Parses emoji strings of one of the following forms
            `<a:name:id> or fallback`
            `<:name:id> or fallback`
            `<a:name:id>`
            `<:name:id>`
        """
        splits = emojistr.rsplit(' or ', maxsplit=1)

        fallback = splits[1] if len(splits) > 1 else None
        emojistr = splits[0].strip('<> ')
        animated, name, id = emojistr.split(':')
        return cls(
            name=name,
            fallback=PartialEmoji(name=fallback),
            animated=bool(animated),
            id=int(id)
        )
