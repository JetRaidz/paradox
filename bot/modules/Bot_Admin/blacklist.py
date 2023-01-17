import asyncio

from registry import tableSchema, Column, ColumnType, tableInterface
from wards import is_master
from utils.lib import paginate_list
from utils.interactive import pager  # noqa

from .module import bot_admin_module as module


@module.cmd("blacklist",
            desc="Add or remove a user from the blacklist.",
            flags=['add', 'remove'])
@is_master()
async def blacklist_cmd(ctx, flags):
    """
    Usage``:
        {prefix}blacklist
        {prefix}blacklist --add userid1, userid2, ...
        {prefix}blacklist --remove userid1, userid2, ...
    Description:
        If a user is on the blacklist, all messages from that user will be ignored before parsing.

        The cached blacklist refreshes every 5 minutes, in case of external changes.
        Running this command will also manually refresh the blacklist.
    """
    refresh_blacklist(ctx.client)
    blacklist_interface = ctx.client.data.admin_user_blacklist

    if flags['add'] or flags['remove']:
        if not ctx.args:
            return await ctx.error_reply("No users given to add or remove.")
        useridstrs = [chars.strip() for chars in ctx.args.split(',')]
        if not all(useridstr.isdigit() for useridstr in useridstrs):
            return await ctx.reply("Userids provided must be numbers.")
        userids = [int(useridstr) for useridstr in useridstrs]

        if flags['add']:
            blacklist_interface.insert_many(
                *((userid, ctx.author.id) for userid in userids),
                insert_keys=('userid', 'added_by')
            )
            ctx.client.objects['user_blacklist'].update(userids)
            await ctx.reply("Users blacklisted.")
        elif flags['remove']:
            blacklist_interface.delete_where(
                userid=userids
            )
            ctx.client.objects['user_blacklist'].difference_update(userids)
            await ctx.reply("Users removed from the blacklist.")
    else:
        blacklist = blacklist_interface.select_where()
        if not blacklist:
            return await ctx.reply("No users blacklisted.")

        blacklist_strs = [
            "{} by {}".format(buser['userid'], buser['added_by'])
            for buser in blacklist
        ]
        await ctx.pager(paginate_list(blacklist_strs, title="User blacklist"), locked=False)


def refresh_blacklist(client):
    client.objects['user_blacklist'] = set(
        (buser['userid'] for buser in client.data.admin_user_blacklist.select_where())
    )


async def autorefresher(client):
    while True:
        refresh_blacklist(client)
        await asyncio.sleep(300)


@module.init_task
def attach_user_blacklist(client):
    client.objects['user_blacklist'] = set()


@module.launch_task
async def launch_user_blacklist_monitor(client):
    asyncio.ensure_future(autorefresher(client))


schema = tableSchema(
    "admin_user_blacklist",
    Column('userid', ColumnType.SNOWFLAKE, primary=True, required=True),
    Column('added_by', ColumnType.SNOWFLAKE, required=True),
)


# Attach data interface
@module.data_init_task
def attach_user_blacklist_data(client):
    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, schema),
        "admin_user_blacklist"
    )
