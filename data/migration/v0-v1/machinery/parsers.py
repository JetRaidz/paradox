import json


def STRING(value):
    """
    Basic parser for a stringy value
    Returns None for empty strings
    """
    parsed = json.loads(value)
    if parsed is None:
        return None
    elif not isinstance(parsed, str):
        print("Ignoring non-string value in string parser: {}".format(parsed))
        return None
    elif len(parsed) == 0:
        return None
    else:
        return parsed


def ID(value):
    """
    Parse a string id into an integer.
    Return None for `0` or none-like values.
    """
    parsed = json.loads(value)
    if parsed is None:
        return None
    elif len(parsed) == 0:
        return None
    else:
        parsed = int(parsed)
        if parsed == 0:
            return None
        else:
            return parsed


def BOOL(value):
    """
    Parse a boolean into a boolean.
    """
    parsed = json.loads(value)
    if parsed is None:
        return None
    else:
        return bool(parsed)


def TRUEBOOL(value):
    """
    Parse a true boolean into a boolean.
    A False value will return None.
    """
    parsed = BOOL(value)
    return parsed if parsed is True else None


def FALSEBOOL(value):
    """
    Parse a true boolean into a boolean.
    A TRUE value will return None.
    """
    parsed = BOOL(value)
    return parsed if parsed is False else None


def STRING_LIST(value):
    """
    Parse a list of strings
    """
    parsed = json.loads(value)
    return parsed


def UNIQUE_STRING_LIST(value):
    """
    Parse a list of strings, and filter for unique ones
    """
    parsed = STRING_LIST(value)
    if parsed is not None:
        parsed = list(set(parsed))
        return parsed


def DISABLED_CMD_LIST(value):
    """
    Reparse the list of disabled commands
    """
    parsed = UNIQUE_STRING_LIST(value)
    if parsed is not None:
        parsed = [value for value in parsed if value.isalpha()]


def ID_LIST(value):
    """
    Parse a list of ids
    """
    parsed = json.loads(value)
    if parsed is not None:
        return [int(item) for item in parsed]


def RECEPTIONSTRING(value):
    """
    Parse as a string, replacing the old FMTSTRING keys with the new keys.
    """
    parsed = STRING(value)  # type: str
    if parsed:
        parsed = parsed.replace('$username$', '{name}')
        parsed = parsed.replace('$mention$', '{mention}')
        parsed = parsed.replace('$server$', '{guildname}')
        return parsed


def TEX_KEEPMSG(value):
    """
    Parse a keepmsg boolean into a keepsourcefor time
    """
    parsed = BOOL(value)
    if parsed is not None:
        return None if parsed is True else 0


def TEX_SHOWNAME(value):
    """
    Parse a showname boolean into a namestyle enum
    """
    parsed = BOOL(value)
    if parsed is not None:
        return 2 if parsed is True else 0
