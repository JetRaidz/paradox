import discord
from datetime import datetime


class ModEvent:
    """
    TODO: Ticket numbers and stuff.
    """
    actions = {
        "ban": ("User Banned", discord.Colour.red()),
        "multi-ban": ("Users Banned", discord.Colour.red()),
        "hackban": ("User Hackbanned", discord.Colour.red()),
        "multi-hackban": ("Users Hackbanned", discord.Colour.red()),
        "kick": ("User Kicked", discord.Colour.orange()),
        "multi-kick": ("Users Kicked", discord.Colour.orange()),
        "unban": ("User Unbanned", discord.Colour.purple()),
        "multi-unban": ("Users Unbanned", discord.Colour.purple()),
        "mute": ("User Muted", discord.Colour.gold()),
        "multi-mute": ("Users Muted", discord.Colour.gold()),
        "unmute": ("User Unmuted", discord.Colour.green()),
        "multi-unmute": ("Users Unmuted", discord.Colour.green()),
        "softban": ("User Softbanned", discord.Colour.orange()),
        "multi-softban": ("Users Softbanned", discord.Colour.orange())
    }

    def __init__(self, ctx, action, mod, users, reason="None", timeout=None):
        self.ctx = ctx
        self.action = action
        self.mod = mod
        self.users = users
        self.user_strs = ["`{}`: {}".format(user.id, user.__str__()) for user in users]
        self.timeout = timeout
        self.reason = reason
        self.init_time = datetime.utcnow()
        self.embed = None

    async def embedify(self):
        """
        TODO: timeout in sensible form
        """
        embed = discord.Embed(title=self.actions[self.action][0], color=self.actions[self.action][1], timestamp=self.init_time)
        embed.add_field(name="User{}".format("s" if len(self.users) > 1 else ""), value="\n".join(self.user_strs), inline=False)
        if self.timeout is not None:
            embed.add_field(name="Expires:", value=self.ctx.strfdelta(self.timeout), inline=False)
        embed.add_field(name="Reason", value=self.reason, inline=False)
        embed.set_footer(icon_url=self.mod.display_avatar, text="Acting Moderator: {}".format(self.mod))
        self.embed = embed
        return embed

    async def modlog_post(self):
        """
        TODO: When channel is retrieved as a channel, some bits won't be required.
        """
        modlog = await self.ctx.server_conf.modlog_ch.get(self.ctx)
        if not modlog:
            return -1
        modlog = self.ctx.server.get_channel(modlog)
        if not modlog:
            return 2
        if not self.embed:
            await self.embedify()
        try:
            self.modlog_msg = await self.ctx.bot.send_message(modlog, embed=self.embed)
        except discord.Forbidden:
            return 1
        except Exception:
            return 3
        return 0
