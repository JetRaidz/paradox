from .PropAction import PropAction, InsertType, ColumnKeys
from . import parsers

tables = {
#    'members_long': {
#        'persistent_roles': PropAction(
#            'persistent_roles',
#            parsers.ID_LIST,
#            'member_stored_roles',
#            InsertType.MANY,
#            {'userid': ColumnKeys.USERID, 'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE}
#        ),
#    },
    'servers': {
        'latex_listen_enabled': PropAction(
            'latex_listen_enabled',
            parsers.BOOL,
            'guild_latex_config',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'autotex': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('guildid',)
        ),
        'texit_latex_listen_enabled': PropAction(
            'latex_listen_enabled',
            parsers.FALSEBOOL,
            'guild_latex_config',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'autotex': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('guildid', 'app')
        ),
        'guild_prefix': PropAction(
            'guild_prefix',
            parsers.STRING,
            'guild_prefixes',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'prefix': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'texit_guild_prefix': PropAction(
            'guild_prefix',
            parsers.STRING,
            'guild_prefixes',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'prefix': ColumnKeys.VALUE, 'app': 'texit'}
        ),
        'role_persistence': PropAction(
            'role_persistence',
            parsers.TRUEBOOL,
            'guild_role_persistence',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'app': 'texit'}
        ),
        'maths_channels': PropAction(
            'maths_channels',
            parsers.ID_LIST,
            'guild_latex_channels',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'texit_maths_channels': PropAction(
            'maths_channels',
            parsers.ID_LIST,
            'guild_latex_channels',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'texit'}
        ),
        'banned_cmds': PropAction(
            'banned_cmds',
            parsers.DISABLED_CMD_LIST,
            'guild_disabled_commands',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'command_name': ColumnKeys.VALUE, 'app': 'texit'},
            {'guildid': ColumnKeys.SERVERID, 'command_name': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'channel_blacklist': PropAction(
            'channel_blacklist',
            parsers.ID_LIST,
            'guild_disabled_channels',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'texit_channel_blacklist': PropAction(
            'channel_blacklist',
            parsers.ID_LIST,
            'guild_disabled_channels',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'texit'}
        ),
        'clean_channels': PropAction(
            'clean_channels',
            parsers.ID_LIST,
            'guild_cleaned_channels',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'texit_clean_channels': PropAction(
            'clean_channels',
            parsers.ID_LIST,
            'guild_cleaned_channels',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'texit'}
        ),
        'join_ch': PropAction(
            'join_ch',
            parsers.ID,
            'guild_greetings',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('guildid', 'app')
        ),
        'texit_join_ch': PropAction(
            'join_ch',
            parsers.ID,
            'guild_greetings',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('guildid', 'app')
        ),
        'leave_ch': PropAction(
            'join_ch',
            parsers.ID,
            'guild_farewells',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('guildid', 'app')
        ),
        'texit_leave_ch': PropAction(
            'leave_ch',
            parsers.ID,
            'guild_farewells',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'channelid': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('guildid', 'app')
        ),
        'mod_role': PropAction(
            'mod_role',
            parsers.ID,
            'guild_modroles',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE}
        ),
        'mute_role': PropAction(
            'mute_role',
            parsers.ID,
            'guild_muteroles',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE}
        ),
        'wolf_app_id': PropAction(
            'wolf_app_id',
            parsers.STRING,
            'guild_wolfram_appid',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'appid': ColumnKeys.VALUE}
        ),
        'guild_autorole': PropAction(
            'guild_autorole',
            parsers.ID,
            'guild_autoroles',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'texit_guild_autorole': PropAction(
            'guild_autorole',
            parsers.ID,
            'guild_autoroles',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE, 'app': 'texit'}
        ),
        'guild_autorole_bot': PropAction(
            'guild_autorole_bot',
            parsers.ID,
            'guild_bot_autoroles',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'texit_guild_autorole_bot': PropAction(
            'guild_autorole_bot',
            parsers.ID,
            'guild_bot_autoroles',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE, 'app': 'texit'}
        ),
        'guild_autoroles': PropAction(
            'guild_autoroles',
            parsers.ID_LIST,
            'guild_autoroles',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE, 'app': 'paradox'}
        )
    },
    'servers_long': {
        'server_latex_preamble': PropAction(
            'server_latex_preamble',
            parsers.STRING,
            'guild_latex_preambles',
            InsertType.INSERT,
            {'guildid': ColumnKeys.SERVERID, 'preamble': ColumnKeys.VALUE}
        ),
        'self_roles': PropAction(
            'self_roles',
            parsers.ID_LIST,
            'guild_selfroles',
            InsertType.MANY,
            {'guildid': ColumnKeys.SERVERID, 'roleid': ColumnKeys.VALUE}
        ),
        'join_msgs_msg': PropAction(
            'join_msgs_msg',
            parsers.RECEPTIONSTRING,
            'guild_greetings',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'message': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('guildid', 'app')
        ),
        'texit_join_msgs_msg': PropAction(
            'join_msgs_msg',
            parsers.RECEPTIONSTRING,
            'guild_greetings',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'message': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('guildid', 'app')
        ),
        'leave_msgs_msg': PropAction(
            'leave_msgs_msg',
            parsers.RECEPTIONSTRING,
            'guild_farewells',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'message': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('guildid', 'app')
        ),
        'texit_leave_msgs_msg': PropAction(
            'leave_msgs_msg',
            parsers.RECEPTIONSTRING,
            'guild_farewells',
            InsertType.UPSERT,
            {'guildid': ColumnKeys.SERVERID, 'message': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('guildid', 'app')
        ),
    },
    'users': {
        'tz': PropAction(
            'tz',
            parsers.STRING,
            'user_time_settings',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'timezone': ColumnKeys.VALUE},
            constraint=('userid',)
        ),
        'brief_time': PropAction(
            'brief_time',
            parsers.BOOL,
            'user_time_settings',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'brief_display': ColumnKeys.VALUE},
            constraint=('userid',)
        ),
        'custom_prefix': PropAction(
            'custom_prefix',
            parsers.STRING,
            'user_prefixes',
            InsertType.INSERT,
            {'userid': ColumnKeys.USERID, 'prefix': ColumnKeys.VALUE, 'app': 'paradox'}
        ),
        'texit_custom_prefix': PropAction(
            'custom_prefix',
            parsers.STRING,
            'user_prefixes',
            InsertType.INSERT,
            {'userid': ColumnKeys.USERID, 'prefix': ColumnKeys.VALUE, 'app': 'texit'}
        ),
        'latex_colour': PropAction(
            'latex_colour',
            parsers.STRING,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'colour': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('userid', 'app')
        ),
        'texit_latex_colour': PropAction(
            'latex_colour',
            parsers.STRING,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'colour': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('userid', 'app')
        ),
        'tex_listening': PropAction(
            'tex_listening',
            parsers.BOOL,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'autotex': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('userid', 'app')
        ),
        'texit_tex_listening': PropAction(
            'tex_listening',
            parsers.BOOL,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'autotex': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('userid', 'app')
        ),
        'latex_keep_message': PropAction(
            'latex_keep_message',
            parsers.TEX_KEEPMSG,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'keepsourcefor': ColumnKeys.VALUE, 'app': 'paradox'},
            {'userid': ColumnKeys.USERID, 'keepsourcefor': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('userid', 'app')
        ),
        'latex_alwaysmath': PropAction(
            'latex_always_math',
            parsers.BOOL,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'alwaysmath': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('userid', 'app')
        ),
        'texit_latex_alwaysmath': PropAction(
            'latex_always_math',
            parsers.BOOL,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'alwaysmath': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('userid', 'app')
        ),
        'latex_showname': PropAction(
            'latex_showname',
            parsers.TEX_SHOWNAME,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'namestyle': ColumnKeys.VALUE, 'app': 'paradox'},
            constraint=('userid', 'app')
        ),
        'texit_latex_showname': PropAction(
            'latex_showname',
            parsers.TEX_SHOWNAME,
            'user_latex_config',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'namestyle': ColumnKeys.VALUE, 'app': 'texit'},
            constraint=('userid', 'app')
        ),
    },
    'users_long': {
        'latex_preamble': PropAction(
            'latex_preamble',
            parsers.STRING,
            'user_latex_preambles',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'preamble': ColumnKeys.VALUE},
            constraint=('userid',)
        ),
        'previous_preamble': PropAction(
            'previous_preamble',
            parsers.STRING,
            'user_latex_preambles',
            InsertType.UPSERT,
            {'userid': ColumnKeys.USERID, 'previous_preamble': ColumnKeys.VALUE},
            constraint=('userid',)
        ),
    }
}
