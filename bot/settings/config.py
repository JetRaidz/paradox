class _guild_config:
    """
    Namespace class to hold the guild settings.
    """
    settings = {}
    __slots__ = tuple()

    def __init__(self):
        pass

    def attach_setting(self, cls):
        self.settings[cls.attr_name] = cls

    def __contains__(self, item):
        return item in self.settings

    def __getattr__(self, attr):
        return self.settings.get(attr)

    def __getitem__(self, item):
        return self.settings.get(item)

    def __setitem__(self, item, value):
        self.settings[item] = value


guild_config = _guild_config()
