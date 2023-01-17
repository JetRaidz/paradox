from .module import latex_module as module


async def latex_exthelp(ctx):
    await ctx.reply("Please see `{}help tex` for help with the `tex` command. "
                    "Extended documentation on LaTeX usage coming soon!".format(ctx.best_prefix()))


@module.init_task
def attach_latex_exthelp(client):
    pass
