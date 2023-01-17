INSERT INTO VERSION (version, updated_by) VALUES (3, 'Initial Creation');


CREATE TABLE guild_moderation_tickets(
	ticketid INTEGER PRIMARY KEY AUTOINCREMENT ,
	ticket_type INTEGER NOT NULL,
	guildid INTEGER NOT NULL,
	modid INTEGER NOT NULL,
	agentid INTEGER NOT NULL,
	app TEXT NOT NULL,
	msgid INTEGER,
	auditid INTEGER,
	reason TEXT,
	created_at INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guild_moderation_ticket_members(
	ticketid INTEGER NOT NULL,
	memberid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (ticketid) REFERENCES guild_moderation_tickets(ticketid) ON DELETE CASCADE
);

CREATE TABLE guild_timed_mute_tickets(
	ticketid INTEGER NOT NULL,
	duration INTEGER NOT NULL,
	roleid INTEGER NOT NULL,
	unmute_timestamp INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (ticketid) REFERENCES guild_moderation_tickets(ticketid) ON DELETE CASCADE
);

CREATE VIEW
    guild_moderation_tickets_combined
AS
SELECT
    t.ticketid AS ticketid,
    t.ticket_type AS ticket_type,
    t.guildid AS guildid,
    t.modid AS modid,
    t.agentid AS agentid,
    t.app AS app,
    t.msgid AS msgid,
    t.auditid AS auditid,
    t.reason AS reason,
    t.created_at AS created_at,
    row_number() OVER (PARTITION BY t.guildid ORDER BY t.ticketid) AS ticketgid,
    timedmutes.duration AS tmute_duration,
    timedmutes.roleid AS tmute_roleid,
    timedmutes.unmute_timestamp AS tmute_unmute_timestamp
FROM
    guild_moderation_tickets t
LEFT JOIN guild_timed_mute_tickets timedmutes ON t.ticketid = timedmutes.ticketid;


CREATE TABLE guild_modlogs(
	guildid INTEGER NOT NULL,
	channelid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid)
);


CREATE TABLE guild_timed_mute_members(
	ticketid INTEGER NOT NULL,
	memberid INTEGER NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ticketid,memberid),
	FOREIGN KEY (ticketid) REFERENCES guild_moderation_tickets(ticketid) ON DELETE CASCADE
);
