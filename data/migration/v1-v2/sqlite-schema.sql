INSERT INTO VERSION (version, updated_by) VALUES (2, 'v1-v2 Migration');


CREATE TABLE member_traffic(
	guildid INTEGER NOT NULL,
	userid INTEGER NOT NULL,
	first_joined INTEGER,
	last_joined INTEGER,
	last_departure INTEGER,
	departure_name TEXT,
	departure_nickname TEXT,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid,userid)
);

CREATE TABLE guild_logging_joins(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_logging_departures(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);


CREATE TABLE guild_userupdate_channel(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_userupdate_events(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	event INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,event)
);

CREATE TABLE guild_userupdate_ignores(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	userid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid,userid)
);


INSERT INTO VERSION (version, updated_by) VALUES (2, 'v1-v2 Migration');

CREATE TABLE guild_starboards(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	channelid INTEGER,
	emoji TEXT,
	threshold INTEGER NOT NULL DEFAULT 1,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE guild_starboard_roles(
	app TEXT NOT NULL,
	guildid INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,guildid)
);

CREATE TABLE message_stars(
	app TEXT NOT NULL,
	msgid INTEGER NOT NULL,
	starmsgid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (app,msgid)
);
