CREATE TABLE VERSION(
	version INTEGER NOT NULL,
	updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_by TEXT,
	PRIMARY KEY (version)
);
INSERT INTO VERSION (version, updated_by) VALUES (1, 'Initial Creation');

CREATE TABLE admin_snippets(
	name TEXT NOT NULL,
	author INTEGER NOT NULL,
	description TEXT NOT NULL,
	content TEXT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (name)
);

CREATE TABLE admin_user_blacklist(
	userid INTEGER NOT NULL,
	added_by INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (userid)
);

CREATE TABLE user_prefixes(
	app TEXT NOT NULL,
	userid INTEGER NOT NULL,
	prefix TEXT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,userid)
);

CREATE TABLE user_latex_preambles(
	userid INTEGER NOT NULL,
	preamble TEXT,
	previous_preamble TEXT,
	whitelisted BOOL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (userid)
);

CREATE TABLE guild_latex_preambles(
	guildid INTEGER NOT NULL,
	preamble TEXT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid)
);

CREATE TABLE user_pending_preambles(
	userid INTEGER NOT NULL,
	app TEXT NOT NULL,
	username TEXT NOT NULL,
	pending_preamble TEXT NOT NULL,
	pending_preamble_diff TEXT,
	submission_time INTEGER NOT NULL,
	submission_message_id INTEGER,
	submission_summary TEXT NOT NULL,
	submission_source_id INTEGER NOT NULL,
	submission_source_name TEXT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (userid)
);

CREATE TABLE global_latex_presets(
	name TEXT NOT NULL,
	preset TEXT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE global_latex_package_whitelist(
	package TEXT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guild_latex_config(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	autotex BOOL,
	autotex_level INTEGER,
	require_codeblocks BOOL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_latex_channels(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,channelid)
);

CREATE TABLE user_latex_config(
	app TEXT NOT NULL,
	userid INTEGER NOT NULL,
	autotex BOOL,
	keepsourcefor INTEGER,
	colour TEXT,
	alwaysmath BOOL,
	alwayswide BOOL,
	namestyle INTEGER,
	autotex_level INTEGER,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,userid)
);

CREATE TABLE guild_wolfram_appid(
	guildid INTEGER NOT NULL,
	appid TEXT,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid)
);

CREATE TABLE user_time_settings(
	userid INTEGER NOT NULL,
	timezone TEXT,
	brief_display BOOL DEFAULT False,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (userid)
);

CREATE TABLE guild_selfroles(
	guildid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid,roleid)
);

CREATE TABLE guild_modroles(
	guildid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid)
);

CREATE TABLE guild_muteroles(
	guildid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid)
);

CREATE TABLE guild_autoroles(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,roleid)
);

CREATE TABLE guild_bot_autoroles(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,roleid)
);

CREATE TABLE guild_greetings(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER,
	message TEXT,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_farewells(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER,
	message TEXT,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_disabled_channels(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,channelid)
);

CREATE TABLE guild_cleaned_channels(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER NOT NULL,
	delay INTEGER NOT NULL DEFAULT 60,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,channelid)
);

CREATE TABLE guild_role_persistence(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_role_persistence_ignores(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,roleid)
);

CREATE TABLE member_stored_roles(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	userid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,userid)
);

CREATE TABLE guild_prefixes(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	prefix TEXT,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_disabled_commands(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	command_name TEXT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,command_name)
);
