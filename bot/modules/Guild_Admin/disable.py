from cmdClient.lib import SafeCancellation

from settings import ListData, StringList, GuildSetting
from registry import tableInterface, Column, ColumnType, tableSchema

from .module import guild_admin_module as module

from wards import in_guild, guild_manager


protected_commands = ['list', 'help', 'support', 'disable', 'config']


@module.cmd("disable",
            desc="Disable commands in this guild.",
            aliases=["enable"])
@in_guild()
@guild_manager()
async def cmd_disable(ctx):
    """
    Usage``:
        {prefix}disable
        {prefix}disable cmd1, cmd2
        {prefix}enable cmd1, cmd2
    Description:
        Manage the disabled commands in this guild.

        With no input, lists the current disabled commands.

        Provided commands must be separated by commas.
        Any aliases may be used for a command, and disabling an alias will disable the whole command.
        See `{prefix}ls` for the available commands.

        Several non-command features, such as persistent roles and automatic latex compilation,\
            are instead managed via the `config` command.
        See `{prefix}config help` for more information about these features.

        Administrators may still use the disabled commands.

        This command requires the `MANAGE GUILD` permission.
    Example``:
        {prefix}disable echo, secho
    """
    # Get currently disabled commands
    disabled = ctx.client.objects["disabled_guild_commands"].get(ctx.guild.id, [])

    if not ctx.args:
        # List disabled commands.
        if not disabled:
            await ctx.reply("No commands have been disabled.")
        else:
            await ctx.reply(
                "Disabled commands in this guild:{cmd_str}"
                "Use `{prefix}disable cmd1, cmd2, ...` to disable commands.\n"
                "Use `{prefix}enable cmd1, cmd2, ...` to renable commands.".format(
                    prefix=ctx.best_prefix(),
                    cmd_str="```css\n{}\n```".format(', '.join(disabled))
                )
            )
    else:
        # Parse arguments
        cmd_strs = [chars.strip().lower() for chars in ctx.args.split(',')]

        # Handle nonexistent commands
        nonexistent = [cmd_str for cmd_str in cmd_strs if cmd_str not in ctx.client.cmd_names]
        if nonexistent:
            if len(nonexistent) == 1:
                await ctx.error_reply("Command or alias `{}` doesn't exist!".format(nonexistent[0]))
            else:
                await ctx.error_reply("The following are not valid commands or aliases!\n`{}`".format(
                    "`, `".join(nonexistent)
                ))
            return

        # Get the actual commands, remove duplicates
        cmdnames = list(set(ctx.client.cmd_names[cmd_str].name for cmd_str in cmd_strs))

        # Handle protected commands
        if any(cmdname in protected_commands for cmdname in cmdnames):
            return await ctx.error_reply(
                "Protected commands:\n`{}`".format('`, `'.join(protected_commands))
            )

        if ctx.alias == 'disable':
            # Add new disabled commands
            ctx.get_guild_setting.disabled_commands.disable(*cmdnames)
        elif ctx.alias == 'enable':
            # Remove disabled commands
            ctx.get_guild_setting.disabled_commands.enable(*cmdnames)

        if len(cmdnames) == 1:
            await ctx.reply(
                "The `{}` and its aliases have been {}d.".format(cmdnames[0], ctx.alias)
            )
        else:
            await ctx.reply(
                "The following commands and their aliases have been {}d:\n`{}`".format(
                    ctx.alias,
                    "`, `".join(cmdnames)
                )
            )


@module.guild_setting
class disabled_commands(ListData, StringList, GuildSetting):
    attr_name = "disabled_commands"
    category = "Guild admin"

    name = "disabled_commands"
    desc = "List of commands to ignore."

    long_desc = (
        "List of commands which are ignored in this guild.\n"
        "Please use the `disable` command to modify this setting.\n"
        "For more information, see `help disable`."
    )

    _table_interface_name = "guild_disabled_commands"
    _data_column = "command_name"

    @classmethod
    async def _parse_userstr(cls, ctx, guildid, userstr, **kwargs):
        """
        Reject modification by this method, unless input is `None`.
        """
        if userstr.lower() == 'none':
            return None

        # TODO: Refactor and add the command parsing system here as well
        raise SafeCancellation("Please use the `disable` command to modify this setting.")

    def disable(self, *cmdnames):
        self.value = list(set(self.value + list(cmdnames)))

    def enable(self, *cmdnames):
        self.value = [item for item in self.value if item not in cmdnames]

    def write(self, **kwargs):
        """
        Adds a write hook to update the cached guild disabled commands
        """
        # TODO: We could also read it in again?
        super().write(**kwargs)

        # Update disabled command cache for the current guild
        if not self.data:
            self.client.objects['disabled_guild_commands'].pop(self.guildid, None)
        else:
            self.client.objects['disabled_guild_commands'][self.guildid] = self.value

    @classmethod
    def initialise(cls, client):
        """
        Load the disabled commands into cache.
        """
        disabled_commands = {}
        command_counter = 0

        rows = client.data.guild_disabled_commands.select_where()
        for row in rows:
            if row['guildid'] not in disabled_commands:
                disabled_commands[row['guildid']] = []
            disabled_commands[row['guildid']].append(row['command_name'])
            command_counter += 1

        client.objects['disabled_guild_commands'] = disabled_commands
        client.log("Read {} guilds with a total of {} disabled commands".format(
            len(disabled_commands),
            command_counter),
            context="LOAD_DISABLED_COMMANDS"
        )


# Define data schema
schema = tableSchema(
    "guild_disabled_commands",
    Column('app', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('guildid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('command_name', ColumnType.SHORTSTRING, primary=True, required=True)
)


# Attach data interface
@module.data_init_task
def attach_disabled_command_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema, shared=False),
        "guild_disabled_commands"
    )
