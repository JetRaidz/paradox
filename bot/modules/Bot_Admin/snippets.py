import sys
from io import StringIO
import traceback

from registry import tableSchema, Column, ColumnType, tableInterface
from wards import is_master

from .module import bot_admin_module as module


@module.cmd("snippet",
            desc="View, run, or create a code snippet.",
            aliases=['snippets'],
            flags=['create', 'delete'])
@is_master()
async def snippet_cmd(ctx, flags):
    """
    Usage``:
        {prefix}snippet
        {prefix}snippet --create
        {prefix}snippet --delete <snippet>
        {prefix}snippet <snippet> [args]
    Description:
        With no arguments, lists the available snippets.

        With `--create`, begins the snippet creation process.

        In the last form, execute `snippet` with `args` available in the environment.
    """
    snip_interface = ctx.client.data.admin_snippets
    snips = snip_interface.select_where()
    snipmap = {snip['name'].lower(): snip for snip in snips}

    if flags['create']:
        # Create a snippet
        name = await ctx.input("Please enter the snippet name, or `c` to cancel.")
        if name.lower() == 'c':
            return await ctx.error_reply("Cancelling.")
        if ' ' in name:
            return await ctx.error_reply("Snippet names cannot have spaces.")

        desc = await ctx.input("Please enter the snippet description, or `c` to cancel.")
        if desc.lower() == 'c':
            return await ctx.error_reply("Cancelling.")

        content = await ctx.input("Please enter the snippet content, or `c` to cancel. (You have 10 minutes)",
                                  timeout=600)
        if content.lower() == 'c':
            return await ctx.error_reply("Cancelling.")

        snip_interface.insert(
            allow_replace=True,
            author=ctx.author.id,
            name=name,
            description=desc,
            content=content
        )
        await ctx.reply("Snippet `{}` saved.".format(name))
    elif flags['delete']:
        name = ctx.args
        if name.lower() not in snipmap:
            return await ctx.error_reply("Unknown snippet `{}`".format(name))
        name = snipmap[name.lower()]['name']

        snip_interface.delete_where(name=name)
        await ctx.reply("Snippet deleted.")
    elif ctx.args:
        # Run a snippet
        splits = ctx.args.split(maxsplit=1)

        name = splits[0]
        if name.lower() not in snipmap:
            return await ctx.error_reply("Unknown snippet `{}`".format(name))

        snip = snipmap[name.lower()]['content']
        snipargs = splits[1] if len(splits) > 1 else ""

        output, error = await _snip_async(ctx, snip, snipargs)
        await ctx.reply(
            "Ran snippet **{}**\n"
            "Output {}:\n"
            "```py\n{}\n```".format(name,
                                    "error" if error else "",
                                    output)
        )
    else:
        # View snippets
        if not snips:
            return await ctx.reply("There are no snippets set up.")

        snipstrs = [
            "'{}' created by '{}':\n\t{}".format(snip['name'], snip['author'], snip['description'])
            for snip in snips
        ]
        return await ctx.reply("```\n{}\n```".format("\n".join(snipstrs)))


async def _snip_async(ctx, snip, snipargs):
    env = {'ctx': ctx, 'args': snipargs}
    env.update(globals())
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    result = None
    exec_string = "async def _temp_exec():\n"
    exec_string += '\n'.join(' ' * 4 + line for line in snip.split('\n'))
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


schema = tableSchema(
    "admin_snippets",
    Column('name', ColumnType.SHORTSTRING, primary=True, required=True),
    Column('author', ColumnType.SNOWFLAKE, required=True),
    Column('description', ColumnType.MSGSTRING, required=True),
    Column('content', ColumnType.TEXT, required=True)
)


# Attach data interface
@module.data_init_task
def attach_snippet_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema),
        "admin_snippets"
    )
