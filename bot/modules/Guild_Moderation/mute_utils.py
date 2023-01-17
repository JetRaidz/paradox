import discord
from .ModAction import ActionState


async def mute_member(member, muterole, audit_reason=None):
    """
    Mute a given member.
    """
    # Attempt to add the mute role
    try:
        await member.add_roles(muterole, reason=audit_reason)
    except discord.Forbidden:
        return ActionState.IAM_FORBIDDEN
    except discord.HTTPException:
        return ActionState.INTERNAL_UNKNOWN
    else:
        return ActionState.SUCCESS


async def unmute_member(member, muterole, audit_reason=None):
    """
    Unmute a given member.
    """
    # Attempt to remove the mute role
    try:
        await member.remove_roles(muterole, reason=audit_reason)
    except discord.Forbidden:
        return ActionState.IAM_FORBIDDEN
    except discord.HTTPException:
        return ActionState.INTERNAL_UNKNOWN
    else:
        return ActionState.SUCCESS


async def _find_member(guild, memberid):
    """
    Attempt to retrieve a member.
    Either returns the member, None, or throws a Discord exception.
    """
    # Attempt the find the member
    member = guild.get_member(memberid)
    if not member:
        member = await guild.fetch_member(memberid)
    return member


async def unmute_memberid(memberid, muterole, audit_reason=None):
    """
    Attempt to unmute a single member of the given guild.
    """
    # Get the member
    try:
        member = await _find_member(muterole.guild, memberid)
    except discord.Forbidden:
        return ActionState.GUILD_NOTFOUND
    except discord.HTTPException:
        return ActionState.MEMBER_NOTFOUND
    if member is None:
        return ActionState.MEMBER_NOTFOUND

    # Attempt to remove the mute role
    try:
        await member.remove_roles(muterole, reason=audit_reason)
    except discord.Forbidden:
        return ActionState.IAM_FORBIDDEN
    except discord.HTTPException:
        return ActionState.INTERNAL_UNKNOWN
    else:
        return ActionState.SUCCESS
