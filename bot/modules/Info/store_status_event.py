from datetime import datetime


async def store_status(bot, before, after):
    if before.status != after.status:
        status = (str(before.status), str(after.status), int(datetime.utcnow().strftime('%s')))
        old_status = bot.objects["user_status"].pop(before.id, None)
        if old_status is None or status[0] != old_status[0]:
            await bot.data.users.set(before.id, "old_status", status)
            bot.objects["user_status"][before.id] = status


def load_into(bot):
    # bot.data.users.ensure_exists("old_status")
    # bot.objects["user_status"] = {}
    # bot.add_after_event("member_update", store_status)
    pass
