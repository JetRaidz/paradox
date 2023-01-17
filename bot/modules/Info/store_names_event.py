"""
Provides some handlers to save the name and nickname history for users

Handlers:
    store_names:
        Listens to member updates for name/nickname changes and stores them
User data:
    name_history: list
        (app independent, automatic)
        The previous names of a user
Member data:
    nickname_history: list
        (app independent, automatic)
        The previous nicknames for a membet
"""


async def store_names(bot, before, after):
    if before.name != after.name:
        history = await bot.data.users_long.get(before.id, "name_history")
        history = history if history else []
        names = [before.name, after.name]
        history.extend([name for name in names if name not in history])
        history = history[-40:]
        await bot.data.users_long.set(before.id, "name_history", history)

    if before.nick != after.nick:
        history = await bot.data.members_long.get(before.server.id, before.id, "nickname_history")
        history = history if history else []
        names = [before.nick, after.nick]
        history.extend([name for name in names if name not in history and name is not None])
        history = history[-40:]
        await bot.data.members_long.set(before.server.id, before.id, "nickname_history", history)


def load_into(bot):
    bot.data.users_long.ensure_exists("name_history")
    bot.data.members_long.ensure_exists("nickname_history")
    bot.add_after_event("member_update", store_names)
