import sys
import json
import logging
import asyncio
from discord import AllowedMentions

from cmdClient.logger import cmd_log_handler

from utils.lib import mail, split_text
from paraArgs import args

# Setup the logger
logger = logging.getLogger()
log_fmt = logging.Formatter(fmt='[{asctime}][{levelname:^8}] {message}', datefmt='%d/%m | %H:%M:%S', style='{')
term_handler = logging.StreamHandler(sys.stdout)
term_handler.setFormatter(log_fmt)
logger.addHandler(term_handler)
logger.setLevel(logging.INFO)

_client = None


# Define the context log format and attach it to the command logger as well
@cmd_log_handler
def log(message, context="GLOBAL", level=logging.INFO, post=True):
    # Use a single line logging format so the files are more parseable
    logger.log(level, '\b[SHARD {}][{}] {}'.format(
        args.shard or 0,
        str(context).center(22, '='),
        json.dumps(message))
    )

    # Fire and forget to the channel logger, if it is set up
    if post and _client is not None:
        asyncio.ensure_future(live_log(message, context, level))


# Live logger that posts to the logging channels
async def live_log(message, context, level):
    if level >= logging.INFO:
        log_chid = _client.conf.get("log_channel")

        # Generate the log messages
        header = "[{}][Shard {}][{}]".format(logging.getLevelName(level), _client.shard_id, str(context))
        if len(message) > 1900:
            blocks = split_text(message, blocksize=1900, code=False)
        else:
            blocks = [message]

        if len(blocks) > 1:
            blocks = [
                "```md\n{}[{}/{}]\n{}\n```".format(header, i+1, len(blocks), block) for i, block in enumerate(blocks)
            ]
        else:
            blocks = ["```md\n{}\n{}\n```".format(header, blocks[0])]

        # Post the log messages
        if log_chid:
            [await mail(_client, log_chid, content=block, allowed_mentions=AllowedMentions.none()) for block in blocks]

        if level >= logging.ERROR:
            error_chid = _client.conf.get("error_channel")
            if error_chid:
                [
                    await mail(_client,
                               error_chid,
                               content=block,
                               allowed_mentions=AllowedMentions.none()) for block in blocks
                ]


def attach_log_client(client):
    """
    Attach the client to the logger so it can post to the log channels.
    """
    global _client
    _client = client
