import discord


region_map = {
    "brazil": "Brazil",
    "eu-central": "Central Europe",
    "hongkong": "Hong Kong",
    "japan": "Japan",
    "russia": "Russia",
    "singapore": "Singapore",
    "sydney": "Sydney",
    "us-central": "Central United States",
    "us-east": "Eastern United States",
    "us-south": "Southern United States",
    "us-west": "Western United States",
    "eu-west": "Western Europe",
    "vip-amsterdam": "Amsterdam (VIP)",
    "vip-us-east": "Eastern United States (VIP)",
    "india": "India",
    "europe": "Europe",
    "southafrica": "South Africa",
    "frankfurt": "Frankfurt",
    "south-korea": "South Korea",
    "london": "London",
    "amsterdam": "Amsterdam"
}

sorted_cats = [
    "Bot Admin",
    "LaTeX Rendering",
    "Guild Admin",
    "Info",
    "Utility",
    "Fun",
    "Social",
    "Moderation",
    "Mathematics",
    "Meta",
    "Misc"
]

sorted_conf_pages = [
    ("General", ["Guild settings", "Starboard", "LaTeX"]),
    ("Manual Moderation", ["Moderation", "Logging"]),
    ("Join/Leave Messages", ["Join message", "Leave message"])
]

ParaCC = {
    "purple": discord.Colour(int("7927eb", 16)),
    "blue": discord.Colour(int("00a7fe", 16))
}
