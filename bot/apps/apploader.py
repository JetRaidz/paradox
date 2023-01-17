import importlib


def load_app(app_name, client):
    app = importlib.import_module("." + app_name, package=__package__)
    app.load_into(client)
