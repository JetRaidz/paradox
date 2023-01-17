from cmdClient import Context

from .config import guild_config

"""
Adds a guildsetting object to Context
that allows retrieving the current value of a guild setting
"""


class ctxDescriptor:
    def __init__(self, cls):
        self.cls = cls
        self.__name__ = cls.__name__

    def __get__(self, instance, owner):
        if instance is None or not isinstance(instance, Context):
            raise AttributeError(
                "'{}' may only be accessed through an instance of 'Context'.".format(self.__name__)
            )
        return self.cls(instance)


@Context.util
@ctxDescriptor
class get_guild_setting:
    __slots__ = ("ctx",)

    def __init__(self, ctx):
        self.ctx = ctx

    def __getattr__(self, setting_name):
        if not self.ctx.guild:
            raise ValueError("Attempting to access a guild setting outside a guild!")

        return guild_config.settings[setting_name].get(self.ctx.client, self.ctx.guild.id)
