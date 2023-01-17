from cmdClient.lib import SafeCancellation


class BadUserInput(SafeCancellation):
    default_msg = "Couldn't parse user input!"
