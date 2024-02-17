import discord
import aiohttp
import logging

from cmdClient import Context
from config import Conf
from registry import tableSchema, Column, ColumnType, tableInterface

from .module import premium_module as module

patreon_tiers = {
    "3226657": "LOW",
    "3226666": "MIDDLE",
    "3226671": "HIGH",
    None: "NONE"
}


async def fetch_patreon_data(ctx: Context):
    """
    Fetch all of the Patron data from the Patreon API.
    """
    header = {"Authorization": f"Bearer {ctx.conf.get('patreon_token')}"}
    campaign = "https://www.patreon.com/api/oauth2/v2/campaigns/2359100/members?include=user,currently_entitled_tiers&fields%5Buser%5D=social_connections&fields%5Bmember%5D=full_name,is_follower,last_charge_date,last_charge_status,lifetime_support_cents,currently_entitled_amount_cents,patron_status,pledge_relationship_start&page%5Bcount%5D=100"

    try:
        async with aiohttp.ClientSession(headers=header) as sess:
            async with sess.get(campaign, json=header) as res:
                if res.status == 200:
                    res = await res.json()
                else:
                    ctx.log(f"Patreon API returned code {r.status}, skipping initialisation", level=logging.WARNING)
                    return

    except Exception as e:
        ctx.log(f"Encountered a critical error when attempting to fetch data from Patreon. Error: {e}",
                level=logging.ERROR)
        return

    await extract_patron_data(ctx, res)


async def extract_patron_data(ctx: Context, res: dict):

    patrons = {}
    for user in res["data"]:
        pid = user["relationships"]["user"]["data"]["id"]
        status = user["attributes"]["patron_status"]
        last_status = user["attributes"]["last_charge_status"]
        name = user["attributes"]["full_name"]
        total = user["attributes"]["lifetime_support_cents"]
        patron_since = user["attributes"]["pledge_relationship_start"]
        last_charge = user["attributes"]["last_charge_date"]

        tier = user["relationships"]["currently_entitled_tiers"].get("data")
        if tier:
            tierid = tier[0]["id"]
        else:
            tierid = None

        # Convert the Patron's subscribed tier to text for clarity
        try:
            tier = patreon_tiers[tierid]
        except Exception:
            tier = None

        # Exclude users without a status as they are only followers.
        if status:
            patrons[pid] = {"id": pid, "UID": 0, "name": name, "tier": tier, "total": total, "status": status, "last_status": last_status, "last_charge": last_charge, "patron_since": patron_since or None, }

    # Sort through the Patron IDs and attempt to get a connected User ID.
    for i in range(len(res["data"])):

        try:
            pid = res["included"][i]["id"]
            uid = res["included"][i]["attributes"].get("social_connections").get("discord").get("user_id")

            patrons[pid].update({"UID": int(uid)})
        except Exception as e:
            pass


    # Add the patron data to the database, upserting to prevent conflict errors
    # The entitlements column is not inserted here so it can be updated later
    patreon_data = ctx.data.patreon_list
    for p in patrons.values():

        patreon_data.upsert(
        constraint=("patronid"),
        patronid = int(p["id"]),
        userid = p["UID"],
        fullname = p["name"],
        tier = p["tier"],
        total = p["total"],
        status = p["status"],
        last_status = p["last_status"],
        last_charge = p["last_charge"],
        patron_since = p["patron_since"]
        )


patreon_list_schema = tableSchema(
    "patreon_list",
    Column('patronid', ColumnType.INT, primary=True, required=True),
    Column('userid', ColumnType.SNOWFLAKE, required=False),
    Column('fullname', ColumnType.TEXT, required=False),
    Column('tier', ColumnType.TEXT, required=True),
    Column('total', ColumnType.INT, required=True),
    Column('status', ColumnType.TEXT, required=True),
    Column('last_status', ColumnType.TEXT, required=True),
    Column('last_charge', ColumnType.TEXT, required=True),
    Column('patron_since', ColumnType.TEXT, required=True),
    Column('entitlements', ColumnType.TEXT, required=False)
)

@module.init_task
def attach_patreon_data(client: Context):
    client.add_after_event("ready", fetch_patreon_data)

    client.data.attach_interface(
        tableInterface.from_schema(client.data, client.app, patreon_list_schema, shared=True),
        "patreon_list"
    )