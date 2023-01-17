INSERT INTO VERSION (version, updated_by) VALUES (3, 'v2-v3 Migration');


CREATE TABLE guild_moderation_tickets(
	ticketid INT AUTO_INCREMENT ,
	ticket_type INT NOT NULL,
	guildid BIGINT NOT NULL,
	modid BIGINT NOT NULL,
	agentid BIGINT NOT NULL,
	app VARCHAR(64) NOT NULL,
	msgid BIGINT,
	auditid BIGINT,
	reason VARCHAR(2048),
	created_at INT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (ticketid)
);

CREATE TABLE guild_moderation_ticket_members(
	ticketid INT NOT NULL,
	memberid BIGINT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	FOREIGN KEY (ticketid) REFERENCES guild_moderation_tickets(ticketid) ON DELETE CASCADE
);

CREATE TABLE guild_timed_mute_tickets(
	ticketid INT NOT NULL,
	duration INT NOT NULL,
	roleid BIGINT NOT NULL,
	unmute_timestamp INT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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


CREATE TABLE guild_timed_mute_members(
	ticketid INT NOT NULL,
	memberid BIGINT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (ticketid,memberid),
	FOREIGN KEY (ticketid) REFERENCES guild_moderation_tickets(ticketid) ON DELETE CASCADE
);

CREATE TABLE guild_modlogs(
	guildid BIGINT NOT NULL,
	channelid BIGINT NOT NULL,
	_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (guildid)
);




INSERT INTO guild_modlogs
    (guildid, channelid)
SELECT
    servers.serverid as guildid,
    CONVERT(JSON_UNQUOTE(servers.value), UNSIGNED INTEGER) AS channelid
FROM servers
WHERE
    servers.property = 'modlog_ch'
    AND servers.value != 'null';
