import os


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
HELP_FILE = os.path.join(__location__, "help.txt")

with open(HELP_FILE, "r") as help_file:
    help_str = help_file.read()


def load_into(client):
    info = {"dev_list": [299175087389802496, 408905098312548362],
            "info_str": ("I am a multi-purpose server automation bot written in discord.py.\n"
                         "Use `{prefix}help` for information on how to use me, "
                         "and `{prefix}list` to see all my commands!"),
            "invite_link": "http://invite.paradoxical.pw",
            "donate_link": "https://www.patreon.com/texit",
            "support_guild": "https://discord.gg/FY9jH7M",
            "privacy_policy": "https://docs.paradoxical.pw/privacy.pdf",
            "brief": False,
            "app": "",
            "help_str": help_str}
    client.app_info = info
