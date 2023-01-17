import sys
from io import StringIO
import traceback
import asyncio

from cmdClient import Context
from utils.ctx_addons import run_in_shell  # noqa
from wards import is_master

from .module import bot_admin_module as module


"""
Exec level commands to manage the bot.
All commands require master permission.

Commands provided:
    async:
        Executes provided code in an async executor.
    exec:
        Executes code using standard python exec.
    eval:
        Executes code and awaits it if required.
    shell:
        Runs a command in the executing environment
"""


@module.cmd("async",
            desc="Executes async code and displays the output.")
@is_master()
async def cmd_async(ctx: Context):
    """
    Usage``:
        {prefix}async <code>
    Description:
        Runs `<code>` as an asynchronous coroutine and prints the output or error.

        *Requires you to be an owner of the bot.*
    """
    if not ctx.arg_str:
        return await ctx.error_reply("You must give me something to run!")

    output, error = await _async(ctx)
    await ctx.reply("**Async input:**\
                    \n```py\n{}\n```\
                    \n**Output {}:** \
                    \n```py\n{}\n```".format(ctx.arg_str,
                                             "error" if error else "",
                                             output))


@module.cmd("exec",
            desc="Executes python code using exec and displays the output.")
@is_master()
async def cmd_exec(ctx: Context):
    """
    Usage``:
        {prefix}exec <code>
    Description:
        Runs `<code>` in current environment using exec() and prints the output or error.

        *Requires you to be an owner of the bot.*
    """
    if not ctx.arg_str:
        return await ctx.error_reply("You must give me something to run!")

    output, error = await _exec(ctx)
    await ctx.reply("**Exec input:**\
                    \n```py\n{}\n```\
                    \n**Output {}:** \
                    \n```py\n{}\n```".format(ctx.arg_str,
                                             "error" if error else "",
                                             output))


@module.cmd("eval",
            desc="Executes python code using eval and displays the output.",
            flags=['s'])
@is_master()
async def cmd_eval(ctx: Context, flags):
    """
    Usage``:
        {prefix}eval <code> [-s]
    Description:
        Runs `<code>` in current environment using `eval()` and prints the output or error.

        *Requires you to be an owner of the bot.*
    Flags::
        s: Eval silently and don't print any output unless there is an error.
    """
    if not ctx.arg_str:
        return await ctx.error_reply("You must give me something to run!")

    output, error = await _eval(ctx)
    if not flags['s'] or error:
        await ctx.reply("**Eval input:**\
                        \n```py\n{}\n```\
                        \n**Output {}:** \
                        \n```py\n{}\n```".format(ctx.args,
                                                 "error" if error else "",
                                                 output))


@module.cmd("shell",
            desc="Runs a command in the operating environment.")
@is_master()
async def cmd_shell(ctx):
    """
    Usage``:
        {prefix}shell <command>
    Description:
        Runs `<command>` in the operating environment and returns the output in a codeblock.
    """
    if not ctx.arg_str:
        return await ctx.error_reply("You must give me something to run!")

    output = await ctx.run_in_shell(ctx.arg_str)
    await ctx.reply("**Command:**\
                    \n```sh\n{}\n```\
                    \n**Output:** \
                    \n```\n{}\n```".format(ctx.arg_str,
                                           output))


async def _eval(ctx):
    output = None
    try:
        output = eval(ctx.args)
    except Exception:
        return (str(traceback.format_exc()), 1)
    if asyncio.iscoroutine(output):
        output = await output
    return (output, 0)


async def _exec(ctx):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    result = None
    try:
        exec(ctx.args)
        result = (redirected_output.getvalue(), 0)
    except Exception:
        result = (str(traceback.format_exc()), 1)
    finally:
        sys.stdout = old_stdout
    return result


async def _async(ctx):
    env = {'ctx': ctx}
    env.update(globals())
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    result = None
    exec_string = "async def _temp_exec():\n"
    exec_string += '\n'.join(' ' * 4 + line for line in ctx.args.split('\n'))
    try:
        exec(exec_string, env)
        result = (redirected_output.getvalue(), 0)
    except Exception:
        result = (str(traceback.format_exc()), 1)
        return result
    _temp_exec = env['_temp_exec']
    try:
        returnval = await _temp_exec()
        value = redirected_output.getvalue()
        if returnval is None:
            result = (value, 0)
        else:
            result = (value + '\n' + str(returnval), 0)
    except Exception:
        result = (str(traceback.format_exc()), 1)
    finally:
        sys.stdout = old_stdout
    return result
