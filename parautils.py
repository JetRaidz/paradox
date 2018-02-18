'''
    Various helper utility functions for commands
'''

import asyncio
import subprocess
import discord

LOGFILE = "paralog.log"
# Logfile should really not be defined here. Logging should probably be done in a class or something.
# Discord.py v1 will have its own logging anyway.

# ----Helper functions and routines----


async def log(logMessage):
    '''
    Logs logMessage in some nice way.
    '''
    # TODO: Some nicer logging, timestamps, a little bit of context
    # For now just print it.
    print(logMessage)
    with open(LOGFILE, 'a+') as logfile:
        logfile.write("\n" + logMessage + "\n")
    return


async def tail(filename, n):
    p1 = subprocess.Popen('tail -n ' + str(n) + ' ' + filename,
                          shell=True, stdin=None, stdout=subprocess.PIPE)
    out, err = p1.communicate()
    p1.stdout.close()
    return out.decode('utf-8')


async def reply(client, message, content):
    if content == "":
        await client.send_message(message.channel, "Attempted to send an empty message!")
    else:
        await client.send_message(message.channel, content)

async def find_user(client, userstr, server=None, in_server=False):
    if userstr == "":
        return None
    maybe_user_id = userstr.strip('<@!> ')
    if maybe_user_id.isdigit():
        def is_user(member):
            return member.id == maybe_user_id
    else:
        def is_user(member):
            return ((userstr.lower() in member.display_name.lower()) or (userstr.lower() in member.name.lower()))
    if server:
        member = discord.utils.find(is_user, server.members)
    if not (member or in_server):
        member = discord.utils.find(is_user, client.get_all_members)
    return member


async def para_format(client, string, message=None, server=None, member=None, user=None):
    if member:
        user = member
    keydict = {"$servers$": str(len(client.servers)),
               "$users$": str(len(list(client.get_all_members()))),
               "$channels$": str(len(list(client.get_all_channels()))),
               "$username$": user.name if user else "",
               "$mention$": user.mention if user else "",
               "$id$": user.id if user else "",
               "$tag$": str(user) if user else "",
               "$displayname$": user.display_name if user else "",
               "$server$": server.name if server else ""
               }
    for key in keydict:
        string = string.replace(key, keydict[key])
    return string


# ----End Helper functions----
