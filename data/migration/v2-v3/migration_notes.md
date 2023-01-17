# Migration from v2 to v3
Continuing the migration from the `key-value` property tables to individual data tables.

This version migrates the following features:
* guild-modlogs

This version also adds the following tables:
* `guild_moderation_tickets`
    * Stores metadata about moderation tickets
* `guild_moderation_ticket_members`
    * Stores the members associated to each moderation ticket
* `guild_timed_mute_tickets`
    * Stores extra metadata about timed mute tickets
* `guild_moderation_tickets_combined`
    * View combining ticket metadata for different ticket types
* `guild_timed_mute_members`
    * Members of currently active temporary mute groups


# Migration operation
Apply the `mysql-schema.sql` or `sqlite-schema.sql` script to the database, as required.
The `sqlite` migration script does not migrate the old data, only updating the version and creating the new tables.


# Description of each of the properties in the v0 property tables, and subsequent action
Unless explicitly stated, value data is encoded by `json.dumps()` and may be reloaded into the actual values described below by `json.loads()`.

## `servers` table
* `modlog_ch`
    * Property name: `modlog_ch`
    * Application: `None`
    * Type: `str` or literal `null`
    * Description: The id of the moderation log
    * Parse as: `id`
    * Action
        * Target table: `guild_modlogs`
        * Insert type: `upsert`
        * Upsert constraint: `(app, guildid)`
        * Insert keymap: `{'guildid': 'row.serverid', 'channelid': 'row.value'}`
