import traceback
import logging
import asyncio

import discord

from cmdClient import cmdClient, Module
from cmdClient.lib import SafeCancellation
from cmdClient.Check import FailedCheck

from settings import guild_config

from logger import log


class paraModule(Module):
    name = "Base module"

    def __init__(self, *args, description=None, hidden=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.description = description or "Paradox module"
        self.hidden = hidden

        self.data_init_tasks = []
        self.data_initialised = False

        self.guild_settings = []

        self.baseCommand.hidden = False
        self.baseCommand.disabled = False

    def guild_setting(self, cls):
        """
        Class decorator to attach a guild setting
        which will be later loaded on initialisation.
        """
        self.guild_settings.append(cls)
        log("Registering guild setting '{}'.".format(cls.attr_name), context=self.name)
        return cls

    def initialise(self, client):
        if self.guild_settings and not self.initialised:
            log("Attaching guild settings.", context=self.name)
            for setting in self.guild_settings:
                log("Attaching guild setting '{}'.".format(setting.attr_name), context=self.name)
                guild_config.attach_setting(setting)
                setting.initialise(client)

        # Caches we expect
        if "disabled_guild_commands" not in client.objects:
            client.objects["disabled_guild_commands"] = {}
        if "disabled_guild_channels" not in client.objects:
            client.objects["disabled_guild_channels"] = {}

        super().initialise(client)

    async def pre_command(self, ctx):
        if ctx.guild:
            disabled = ctx.client.objects["disabled_guild_commands"]
            if ctx.guild.id in disabled and ctx.cmd.name in disabled[ctx.guild.id]:
                if not ctx.author.guild_permissions.administrator:
                    raise SafeCancellation

            # Handle blacklisted guild channels
            disabled = ctx.client.objects["disabled_guild_channels"]
            if ctx.guild.id in disabled:
                # Handle disabled channels, disabled categories, and threads in disabled channels
                if ctx.ch.id in disabled[ctx.guild.id] or ctx.ch.category_id in disabled[ctx.guild.id] or (ctx.ch.type in (discord.ChannelType.news_thread, discord.ChannelType.public_thread, discord.ChannelType.private_thread) and ctx.ch.parent_id in disabled[ctx.guild.id]):
                    if not ctx.author.guild_permissions.administrator:
                        raise SafeCancellation

    def data_init_task(self, func):
        """
        Decorator which adds a data initialisation task.
        These tasks accept a client,
        but should not set up the client or assume any existing data or schema.
        The primary purpose is to attach the data interfaces for each module.
        """
        self.data_init_tasks.append(func)
        log("Adding data initialisation task '{}'.".format(func.__name__), context=self.name)
        return func

    def initialise_data(self, client):
        """
        Data initialise hook.
        """
        if not self.data_initialised:
            log("Running data initialisation tasks.", context=self.name)

            for task in self.data_init_tasks:
                log("Running data initialisation task '{}'.".format(task.__name__), context=self.name)
                task(client)

            self.data_initialised = True
        else:
            log("Already initialised data, skipping data initialisation.", context=self.name)

    async def on_exception(self, ctx, exception):
        try:
            raise exception
        except (FailedCheck, SafeCancellation):
            # cmdClient generated and handled exceptions
            raise exception
        except (asyncio.CancelledError, asyncio.TimeoutError):
            # Standard command and task exceptions, cmdClient will also handle these
            raise exception
        except discord.Forbidden:
            # Unknown uncaught Forbidden
            try:
                # Attempt a general error reply
                await ctx.reply("I don't have enough permissions here to complete the command!")
            except discord.Forbidden:
                # We can't send anything at all. Exit quietly, but log.
                full_traceback = traceback.format_exc()
                log(("Caught an unhandled 'Forbidden' while "
                     "executing command '{cmdname}' from module '{module}' "
                     "from user '{message.author}' (uid:{message.author.id}) "
                     "in guild '{message.guild}' (gid:{guildid}) "
                     "in channel '{message.channel}' (cid:{message.channel.id}).\n"
                     "Message Content:\n"
                     "{content}\n"
                     "{traceback}\n\n"
                     "{flat_ctx}").format(
                         cmdname=ctx.cmd.name,
                         module=ctx.cmd.module.name,
                         message=ctx.msg,
                         guildid=ctx.guild.id if ctx.guild else None,
                         content='\n'.join('\t' + line for line in ctx.msg.content.splitlines()),
                         traceback=full_traceback,
                         flat_ctx=ctx.flatten()
                     ),
                    context="mid:{}".format(ctx.msg.id),
                    level=logging.WARNING)

        except Exception as e:
            # Unknown exception!
            full_traceback = traceback.format_exc()
            only_error = "".join(traceback.TracebackException.from_exception(e).format_exception_only())
            # Handle the error message being too long to display in the embed
            # Discord can throw error messages over the embed field limit
            if len(only_error) > 500:
                only_error = only_error[:500] + "..."

            log(("Caught an unhandled exception while "
                 "executing command '{cmdname}' from module '{module}' "
                 "from user '{message.author}' (uid:{message.author.id}) "
                 "in guild '{message.guild}' (gid:{guildid}) "
                 "in channel '{message.channel}' (cid:{message.channel.id}).\n"
                 "Message Content:\n"
                 "{content}\n"
                 "Traceback:\n"
                 "{traceback}\n\n"
                 "{flat_ctx}").format(
                     cmdname=ctx.cmd.name,
                     module=ctx.cmd.module.name,
                     message=ctx.msg,
                     guildid=ctx.guild.id if ctx.guild else None,
                     content='\n'.join('\t' + line for line in ctx.msg.content.splitlines()),
                     traceback='\n'.join('\t' + line for line in full_traceback.splitlines()),
                     flat_ctx=ctx.flatten()
                 ),
                context="mid:{}".format(ctx.msg.id),
                level=logging.ERROR)

            error_embed = discord.Embed(title="Something went wrong!")
            error_embed.description = (
                "An unexpected error occurred while processing your command!\n"
                "The error has been reported and should be fixed soon.\n"
                "If the error persists, please contact our friendly support team at "
                "[our support guild]({})!".format(ctx.client.app_info['support_guild'])
            )
            if logging.getLogger().getEffectiveLevel() < logging.INFO:
                error_embed.add_field(
                    name="Exception",
                    value="`{}`".format(only_error)
                )

            await ctx.reply(embed=error_embed)


cmdClient.baseModule = paraModule
