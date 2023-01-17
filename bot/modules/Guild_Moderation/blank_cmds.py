from .module import guild_moderation_module as module

"""
Temporary blanks over the remaining moderation disabled for partial update.
"""


def temp_disabled(func):
    async def _func(ctx):
        """
        Sorry!:
            This command has been temporarily disabled pending the next update.
        """
        await ctx.error_reply(
            "Sorry, the `{}` command has been temporarily disabled pending the next update".format(
                func.__name__[4:]
            )
        )
    return _func


@module.cmd("giverole",
            desc="Give roles to a member.",
            disabled=True)
@temp_disabled
async def cmd_giverole(ctx):
    pass


@module.cmd("rolemod",
            desc="Give/take groups of roles to groups of members.",
            disabled=True)
@temp_disabled
async def cmd_rolemod(ctx):
    pass
