import argparse

# ------------------------------
# Parse commandline arguments
# ------------------------------
parser = argparse.ArgumentParser()
parser.add_argument('--conf',
                    dest='config',
                    default='config/paradox.conf',
                    help="Path to configuration file.")
parser.add_argument('--shard',
                    dest='shard',
                    default=None,
                    type=int,
                    help="Shard number to run, if applicable.")
parser.add_argument('--writeschema',
                    dest='schemafile',
                    default=None,
                    type=str,
                    help="If provided, writes the db schema to the provided file and exits.")
parser.add_argument('--createdb',
                    action='store_true',
                    dest='createdb',
                    help="Attmpt to create the database. This only works for `sqlite`, and should only be run once.")

args = parser.parse_args()
