from paradata_sqlite import BotData as old_botdata
from paradata_mysql import BotData as new_botdata

from botconf import Conf

conf = Conf("paradox.conf")

# This script is for moving the properties in the sqlite database to a new mysql database
# It simultaneously moves several properties with very long values present in the previous version to "long" tables
# These processes will be split up and presented in different scripts in future


print("Establishing old and new data objects")
# Create sqlite connector
old_data = old_botdata(data_file=conf.get("bot_data_file"), app="")
old_conn = old_data.conn

# Fixup
print("Removing strange user mention in userid column")
old_conn.execute("DELETE FROM users WHERE userid LIKE '<%'")
old_conn.commit()

"""
# Dictionary factory for formatting output cursor rows
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
old_conn.row_factory = dict_factory
"""

# Create mysql object
dbopts = {
    'username': conf.get('username'),
    'password': conf.get('password'),
    'host': conf.get('host'),
    'database': conf.get('database')
}
new_data = new_botdata(app="", **dbopts)
new_conn = new_data.conn

# Explicitly list the keys we want to move to the long tables in the process
print("Creating lists of keys to move to the long tables")

# User props to match: name_history, latex_preamble, notifyme, limbo_preamble, piggybank_history
long_user_props = ["name_history", "preamble", "notifyme", "piggybank_history"]

# Server props to match: server_embeds, tags, self_roles, server_latex_preamble, join_msgs_msg, leave_msgs_msg
long_server_props = ["server_embeds", "tags", "self_roles", "server_latex_preamble", "_msg"]

# Member props to match: nickname_history, persistent_roles
long_member_props = ["nickname_history", "persistent_roles"]


def migrate(name, numkeys, long_props):
    print("Migrating {} properties".format(name))

    # Move prop table
    print("> Moving {} property table".format(name))
    props_moved = 0

    sql = "SELECT * FROM {}_props".format(name)
    cursor = old_conn.execute(sql)
    new_cursor = new_conn.cursor()
    for row in cursor.fetchall():
        # Check whether the property needs to be moved to the long table
        is_long = any(row[0].endswith(tail) for tail in long_props)

        # Generate the name of the table to move to
        table = ("{}_long_props" if is_long else "{}_props").format(name)

        # Add the row to this table
        new_cursor.execute("INSERT INTO {} VALUES (%s, %s)".format(table), tuple(row))
        props_moved += 1

    print("> Moved {} rows into the {} property tables, with {} long props".format(props_moved, name, len(long_props)))

    # Move main table
    print("> Moving {} value table".format(name))
    entries_moved = 0
    longs_moved = 0
    data_format = "({}%s)".format("%s, "*(numkeys+1))

    sql = "SELECT * FROM {}".format(name)
    cursor = old_conn.execute(sql)
    for row in cursor.fetchall():
        # Check whether the property needs to be moved to the long table
        is_long = any(row[numkeys].endswith(tail) for tail in long_props)

        # Generate the name of the table to move to
        table = ("{}_long" if is_long else "{}").format(name)

        # Add the row to this table
        new_cursor.execute("INSERT INTO {} VALUES {}".format(table, data_format), tuple(row))
        entries_moved += 1
        longs_moved += 1 if is_long else 0

    print("> Moved {} rows into the {} value tables, with {} rows moved into the long table".format(entries_moved, name, longs_moved))
    print("Migration for {} properties complete!\n".format(name))


if __name__ == "__main__":
    print("Beginning migration")
    migrate("users", 1, long_user_props)
    migrate("members", 2, long_member_props)
    migrate("servers", 1, long_server_props)
