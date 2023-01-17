import sys
import configparser as cfgp

from machinery import connectors
from machinery.properties import tables
from machinery.PropAction import PropAction


# Read in config
config = cfgp.ConfigParser()
config.read("migration.conf")

# Obtain source connector
source_type = config['SOURCE']['type']
if source_type.strip() == 'sqlite':
    source_connector = connectors.sqliteConnector(db_file=config['SOURCE']['db_file'].strip())
else:
    source_connector = connectors.mysqlConnector(
        username=config['SOURCE']['username'].strip(),
        password=config['SOURCE']['password'].strip(),
        host=config['SOURCE']['host'].strip(),
        database=config['SOURCE']['database'].strip(),
    )


# Obtain target connector
target_type = config['TARGET']['type']
if target_type.strip() == 'sqlite':
    target_connector = connectors.sqliteConnector(db_file=config['TARGET']['db_file'].strip())
else:
    target_connector = connectors.mysqlConnector(
        username=config['TARGET']['username'].strip(),
        password=config['TARGET']['password'].strip(),
        host=config['TARGET']['host'].strip(),
        database=config['TARGET']['database'].strip(),
    )


# Attach target connector to propaction
PropAction.attach_connector(target_connector)

# Migrate the data
print("Beginning migration!")
counter = 0
stats = {}
for table, props in tables.items():
    stats[table] = {}
    for row in source_connector.select_where(table):
        if row['property'] in props:
            action = props[row['property']]
            if row['property'] not in stats[table]:
                stats[table][row['property']] = [action, 0]
            stats[table][row['property']][1] += 1
            action.act_on(row)

            counter += 1
            if not counter % 10:
                sys.stdout.write('\r{} rows migrated.'.format(counter))
                sys.stdout.flush()

if counter % 10:
    sys.stdout.write('\r{} rows migrated.'.format(counter))
    sys.stdout.flush()


# Print summary statistics
stat_strs = [
    '\n'.join("{}\t{}.{} -> {}".format(num, table, prop, action.target) for prop, (action, num) in stats[table].items())
    for table in stats
]
print("\n-----Migration Complete-----\n{}".format('\n'.join(stat_strs)))
