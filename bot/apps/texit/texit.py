import os


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
HELP_FILE = os.path.join(__location__, "help.txt")

with open(HELP_FILE, "r") as help_file:
    help_str = help_file.read()


info = {
    "dev_list": [299175087389802496, 408905098312548362],
    "info_str": ("I am a high quality LaTeX rendering bot coded in discord.py.\n"
                 "Use `{prefix}help` for information on how to use me, "
                 "and `{prefix}list` to see all my commands!"),
    "invite_link": "http://texit.paradoxical.pw",
    "donate_link": "https://www.patreon.com/texit",
    "support_guild": "https://discord.gg/FY9jH7M",
    "privacy_policy": "https://docs.paradoxical.pw/privacy.pdf",
    "brief": True,
    "app": "texit",
    "help_str": help_str,
    "help_file": "bot/resources/apps/texit/texit_thanks.png"
}

disabled_modules = [
    "Fun",
    "Social",
]
disabled_commands = {
    'colour',
    'echo',
    'emoji',
    'invitebot',
    'jumpto',
    'names',
    'piggybank',
    'quote',
    'secho'
}


def load_into(client):
    # client.add_after_event("guild_join", enable_latex_listening)
    client.app_info = info

    # Disable and remove the modules and commands we don't want
    for module in client.modules:
        if module.name in disabled_modules:
            module.enabled = False
        else:
            module.cmds = [cmd for cmd in module.cmds if cmd.name not in disabled_commands]

    client.update_cmdnames()

    # Set the default latex guild listening to True
    latex_module = [module for module in client.modules if module.name == "LaTeX Rendering"][0]
    latex_module.LatexGuild.defaults['autotex'] = True
    latex_setting = [
        setting for setting in latex_module.guild_settings if setting.name == "latex"
    ][0]
    latex_setting._default = True
