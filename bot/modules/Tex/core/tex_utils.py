from enum import IntEnum


class TexNameStyle(IntEnum):
    HIDDEN = 0
    USERNAME = 1
    DISPLAYNAME = 2
    NICKNAME = 2
    MENTION = 3


class AutoTexLevel(IntEnum):
    WEAK = 0
    STRICT = 1
    CODEBLOCK = 2


class ParseMode(IntEnum):
    DOCUMENT = 0
    GATHER = 1
    ALIGN = 2
    DEPENDS = 3
    TIKZ = 4
