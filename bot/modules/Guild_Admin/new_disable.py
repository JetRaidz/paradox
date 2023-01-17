from .module import guild_admin_module as module

from wards import in_guild, guild_manager


protected_commands = ['list', 'help', 'support', 'disable', 'config']


@module.cmd("disable",
            desc="Disable features and commands in this guild.",
            aliases=["enable"])
@in_guild()
@guild_manager()
async def cmd_disable(ctx):
    """
    Usage:
        {prefix}disable
        {prefix}disable <commands and features>
        {prefix}enable <commands and features>
    Descriptions:
        Manage the disabled commands and features in this guild.

        With no input, lists the current disabled commands and features.

        Commands and features must be given separated by commands.
        Any aliases may be used for a command, it is not currently possible to disable a single alias.
        See `{prefix}ls` for the available commands.
        See below for the available features.

        Several non-command features, such as persistent roles and automatic latex compilation,\
            are instead managed via the `config` command.
        See `{prefix}config help` for more information about these features.

        This command requires the `MANAGE GUILD` permission.
    Features:
        *Depending on the application, some features and commands may already not be available.*
        The following refers to the modules and commands visible in `{prefix}ls`.

        **latex**: All the commands in the `LaTeX Rendering` module.
        **admin**: All guild admin commands apart from `config` and `disable`.
        **info**: All commands in the `Info` module.
        **utils**: All commands in the `Utility` module.
        **fun**: All the commands in the `Fun` module.
        **maths**: All commands in the `Mathematics` module.
        **meta**: All commands in `Meta` apart from `help`, `list`, and `support`.
        **general-utils**:
    Example:
        {prefix}bancmd secho, echo
    """
    pass
