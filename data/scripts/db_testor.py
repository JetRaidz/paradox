import asyncio

from paradata_mysql import BotData
from botconf import Conf

conf = Conf("paradox.conf")

# Testing data
fakeuser = 123456789
otherfakeuser = 234567890
fakeserver = 987654321

fakedata1 = "abcdefghijklmnopqrstuvwxyz"
fakedata2 = [i for i in range(10)]

# Initialisation data for the sqlite version
"""
dbfile = "testdata.db"

data_noapp = BotData(dbfile, app="")
data_testapp = BotData(dbfile, app="testapp")
"""

# Initialisation data for the mysql version

dbopts = {
    'username': conf.get('username'),
    'password': conf.get('password'),
    'host': conf.get('host'),
    'database': conf.get('database')
}

data_noapp = BotData(app="", **dbopts)
data_testapp = BotData(app="testapp", **dbopts)


print("Initialised data ojects")

# Add some properties to the propmap
print("Adding four properties to user table")
data_testapp.users.ensure_exists("property1", "property2", shared=False)
data_testapp.users.ensure_exists("property3", "property4", shared=True)

print("Adding two properties to member table")
data_noapp.members.ensure_exists("property1", "property2", shared=False)


async def main():
    # Test setting data
    print("Setting user data")
    await data_noapp.users.set(fakeuser, "property1", fakedata1)
    await data_noapp.users.set(otherfakeuser, "property1", fakedata1)
    await data_noapp.users.set(fakeuser, "property2", fakedata2)
    await data_noapp.users.set(fakeuser, "property3", fakedata1)
    await data_noapp.users.set(fakeuser, "property4", fakedata2)

    # Test retrieving data
    print("Retrieving data, checking consistency")
    response = await data_noapp.users.get(fakeuser, "property1")
    if response != fakedata1:
        print("ISSUE: Got\n{}\nfor property1. Expected\n{}".format(response, fakedata1))

    response = await data_noapp.users.get(fakeuser, "property2")
    if response != fakedata2:
        print("ISSUE: Got\n{}\nfor property2. Expected\n{}".format(response, fakedata2))

    # Test that non-existent values produce None
    print("Checking non-existent values")
    response = await data_noapp.users.get(fakeuser + 1, "property1")
    if response is not None:
        print("ISSUE: Retrieving non-existent value did not return None")

    # Test that shared flag works
    print("Testing shared flag behaviour")
    response = await data_testapp.users.get(fakeuser, "property1")
    if response is not None:
        print("ISSUE: Non-shared property property1 is non-empty for app testapp. Value: {}".format(response))

    response = await data_testapp.users.get(fakeuser, "property3")
    if response != fakedata1:
        print("ISSUE: Shared property property3 not consistent for app testapp. Got\n{}\nExpected\n{}".format(response, fakedata1))

    # Test setting member data
    print("Setting member data")
    await data_noapp.members.set(fakeserver, fakeuser, "property1", fakedata1)

    # Test retrieving member data
    print("Retrieving member data")
    response = await data_noapp.members.get(fakeserver, fakeuser, "property1")
    if response != fakedata1:
        print("ISSUE: Got\n{}\nfor property1. Expected\n{}".format(response, fakedata1))

    # Test find
    print("Testing find for user data")
    response = await data_noapp.users.find("property1", fakedata1, read=True)
    if set(response) != {fakeuser, otherfakeuser}:
        print("ISSUE: Got the following response from find:\n{}\nExpecting:\n{}".format(response, [fakeuser, otherfakeuser]))

    response = await data_noapp.users.find("property1", fakedata2, read=True)
    if response != []:
        print("ISSUE: Got unexpected non-empty response from find, response\n{}".formtat(response))

    # Test find not empty
    print("Testing finding non-empty values in user data")
    response = await data_noapp.users.find_not_empty("property1")
    if set(response) != {fakeuser, otherfakeuser}:
        print("ISSUE: Got the following response from find not empty:\n{}\nExpecting:\n{}".format(response, [fakeuser, otherfakeuser]))

    response = await data_noapp.users.find_not_empty("property2")
    if response != [fakeuser]:
        print("ISSUE: Got the following response from find not empty:\n{}\nExpecting:\n{}".format(response, [fakeuser]))

    print("All tests complete")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
