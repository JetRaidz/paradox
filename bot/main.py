import logging

from concurrent_log_handler import ConcurrentRotatingFileHandler

import discord
from cmdClient import cmdClient

from config import Conf
from logger import log, log_fmt, attach_log_client
from apps import load_app
from paraArgs import args

from registry.connectors import mysqlConnector, sqliteConnector
from settings import guild_config

# Always load modules last
from paraData import versionModule  # noqa
import modules  # noqa


# Extract command line arguments
config_file = args.config
shard_num = args.shard or 0
schema_file = args.schemafile
createdb = args.createdb

# ------------------------------
# Load the configuration file
# ------------------------------
section_name = "SHARD {}".format(shard_num) if shard_num is not None else "DEFAULT"
conf = Conf(config_file, section_name)

# ------------------------------
# Read the environment variables
# ------------------------------
PREFIX = conf.get("PREFIX", "~")
CURRENT_APP = conf.get("APP", "paradox")

# Discord channel ids for logging endpoints and internal communication
FEEDBACK_CH = conf.getint("FEEDBACK_CH")
PREAMBLE_CH = conf.getint("PREAMBLE_CH")
GUILD_LOG_CH = conf.getint("GUILD_LOG_CH")
LOG_CHANNEL = conf.getint("LOG_CHANNEL")
ERROR_CHANNEL = conf.getint("ERROR_CHANNEL") or LOG_CHANNEL

# Shard info
SHARD_COUNT = conf.getint("SHARD_COUNT") or 1


# ------------------------------
# Initialise the logger file handler
# ------------------------------
LOGFILE = conf.get("LOGFILE")
LOGLEVEL = (conf.get("LOGLEVEL") or "INFO").strip()
DISCORD_LOGLEVEL = (conf.get("DISCORD_LOGLEVEL") or "INFO").strip()

# Get the logger
logger = logging.getLogger()

# Set the log levels
logger.setLevel(LOGLEVEL)
logging.getLogger('discord').setLevel(DISCORD_LOGLEVEL)

file_handler = ConcurrentRotatingFileHandler(
    filename=LOGFILE,
    maxBytes=50000000,
    backupCount=10,
    encoding='utf-8',
    mode='a'
)
file_handler.setFormatter(log_fmt)
logger.addHandler(file_handler)


# ------------------------------
# Create the client
# ------------------------------

client = cmdClient(
    prefix=PREFIX,
    shard_id=shard_num,
    shard_count=SHARD_COUNT,
    intents=~discord.Intents(presences=True),
    chunk_guilds_at_startup=False
)
client.log = log
client.conf = conf
client.app = CURRENT_APP
client.sharded = (SHARD_COUNT > 1)
client.guild_config = guild_config

# Attach the relevant app information, app modules, and hooks
load_app(CURRENT_APP or "default", client)


# ------------------------------
# Initialise data
# ------------------------------

DB_TYPE = conf.get("DB_TYPE")

# Attach the appropriate database connector
if not DB_TYPE or DB_TYPE.lower() == "sqlite":
    client.data = sqliteConnector(db_file=conf.get("sqlite_db", "data/paradox.db"))
elif DB_TYPE.lower() == "mysql":
    dbopts = {
        'username': conf.get('db_username'),
        'password': conf.get('db_password'),
        'host': conf.get('db_host'),
        'database': conf.get('db_database')
    }
    client.data = mysqlConnector(**dbopts)
else:
    raise Exception("Unknown data storage type {} in configuration".format(DB_TYPE))

# Initialise the module data interfaces
log("Initialising data for all client modules.")
for module in client.modules:
    if module.enabled:
        module.initialise_data(client)

# If the schema was requested, write it here and exit
if schema_file is not None:
    log("Writing schema.")
    with open(schema_file, "w") as f:
        f.write(client.data.get_schema())
    log("Written schema, closing.")
    exit()

# If database creation was requested, attempt it now and exit
if createdb:
    log("Creating database.")
    client.data.create_database()
    log("Created database, closing.")
    exit()


# ------------------------------
# Set up the client
# ------------------------------

# Attach prefix function
client.objects["user_prefix_cache"] = {}
client.objects["guild_prefix_cache"] = {}


@client.set_valid_prefixes
async def get_prefixes(client, message):
    """
    Returns a list of valid prefixes for this message.
    """
    # Add both types of mentions, which are always valid prefixes
    prefixes = [client.user.mention, "<@!{}>".format(client.user.id)]

    # Add user prefix if it exists
    user_prefix = client.objects["user_prefix_cache"].get(message.author.id, None)
    if user_prefix is not None:
        prefixes.append(user_prefix)

    # Add guild prefix if it exists, otherwise add default prefix
    guild_prefix = None
    if message.guild:
        guild_prefix = client.objects["guild_prefix_cache"].get(message.guild.id, None)
    if guild_prefix is not None:
        prefixes.append(guild_prefix)
    else:
        prefixes.append(client.prefix)

    return prefixes


# --------------------------------
# Attach client event hooks
# ------------------------------

@client.event
async def on_ready():
    # Set activity
    activity_name = "Type {}help for usage!".format(client.prefix)
    client.objects["activity_name"] = activity_name
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name=activity_name)
    )

    # Attach global channels
    client.objects["feedback_channel"] = discord.utils.get(client.get_all_channels(), id=FEEDBACK_CH)
    client.objects["preamble_channel"] = discord.utils.get(client.get_all_channels(), id=PREAMBLE_CH)
    client.objects["guild_log_channel"] = discord.utils.get(client.get_all_channels(), id=GUILD_LOG_CH)

    # Launch modules
    await client.launch_modules()

    # Attach the log client and log the alive message
    attach_log_client(client)

    log_msg = ("Logged in as\n{client.user.name} (uid:{client.user.id}).\n"
               "Using configuration \"{app}\".\n"
               "Logged into {n} guilds on shard {shard} with {shard_count} shard(s).\n"
               "Loaded {m} modules with {mn} commands.\n"
               "Listening for {mnn} command keywords.\n"
               "Ready to take commands.".format(
                   client=client,
                   app=client.app_info['app'],
                   shard=shard_num,
                   shard_count=SHARD_COUNT,
                   n=len(client.guilds),
                   m=len(client.modules),
                   mn=len(client.cmds),
                   mnn=len(client.cmd_names)
               ))
    log(log_msg)


@client.event
async def on_message(message: discord.Message):
    # Handle messages from bot accounts
    if message.author.bot and message.author.id not in conf.getintlist("whitelisted_bots", []):
        return

    # Handle messages from blacklisted users
    if message.author.id in conf.getintlist("blacklisted_users", []):
        return
    if message.author.id in client.objects['user_blacklist']:
        return

    if message.guild:
        # Handle messages from blacklisted guilds
        if message.author.id in conf.getintlist("blacklisted_guilds", []):
            return

        # Hack to make sure `ctx.guild.me` is not None
        if message.guild.me is None:
            me = await message.guild.fetch_member(client.user.id)
            message.guild._members[client.user.id] = me

    await client.parse_message(message)


# Initialise modules
client.initialise_modules()


# ----Everything is set up, start the client!----
client.run(conf.get("TOKEN"))
