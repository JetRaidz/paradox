from ..module import latex_module as module

from . import LatexUserSetting
from . import user_data  # noqa


class LatexUser:
    # User configuration settings
    settings = {
        "autotex": LatexUserSetting.autotex,
        "keepsourcefor": LatexUserSetting.keepsourcefor,
        "colour": LatexUserSetting.colour,
        "alwaysmath": LatexUserSetting.alwaysmath,
        "alwayswide": LatexUserSetting.alwayswide,
        "namestyle": LatexUserSetting.namestyle,
        "autotex_level": LatexUserSetting.autotex_level,
    }

    __slots__ = (*settings.keys(), 'id', 'preamble')

    # Stored client for accessing data interfaces
    _client = None

    def __init__(self, id):
        self.id = id

        # Explicitly typed user configuration settings
        self.autotex = None  # type:bool
        self.keepsourcefor = None  # type: int
        self.colour = None  # type: str
        self.alwaysmath = None  # type: bool
        self.alwayswide = None  # type: bool
        self.namestyle = None  # type: TexNameStyle
        self.autotex_level = None  # type: AutoTexLevel

        self.preamble = None  # type: Optional[str]

        # Load the config from data
        self.load()

    def load(self):
        """
        Retrieve the user data from the database
        """
        # Get base config
        rows = self._client.data.user_latex_config.select_where(userid=self.id)
        for name, setting in self.settings.items():
            value = setting._data_to_value(
                self._client,
                self.id,
                setting.default if not rows or rows[0][name] is None else rows[0][name]
            )
            setattr(self, name, value)

        # Get preamble
        rows = self._client.data.user_latex_preambles.select_where(userid=self.id)
        if rows:
            self.preamble = rows[0]['preamble'] or self.preamble

    def get_setting_data(self, name: str):
        """
        Convenience method to retrieve the data for the requested setting.
        """
        if name not in self.settings:
            raise ValueError("Requested setting `{}` does not exist.".format(name))

        setting = self.settings[name]
        value = getattr(self, name)

        return setting._data_from_value(self._client, self.id, value)

    @classmethod
    def get(cls, id):
        return cls(id)


@module.data_init_task
def attach_latexuser_client(client):
    LatexUser._client = client
