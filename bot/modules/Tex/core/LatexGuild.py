from ..module import latex_module as module

from .tex_utils import AutoTexLevel
from . import guild_data  # noqa
from . import guild_config  # noqa


class LatexGuild:
    __slots__ = (
        'id', 'autotex', 'autotex_level', 'require_codeblocks',
        'latex_channels', 'preamble'
    )
    # Cache of all guilds the client requests
    cached_guilds = {}

    # Stored client for accessing data interfaces
    _client = None

    # Defaults
    defaults = {
        "autotex": False,
        "autotex_level": AutoTexLevel.WEAK,
        "require_codeblocks": False,
        "latex_channels": None,
        "preamble": None,
    }

    def __init__(self, id, **kwargs):
        if self._client is None:
            raise RuntimeError("Attempted to get a LatexGuild before data initialisation.")

        self.id = id

        # Whether latex is automatically compiled
        self.autotex = None  # type: bool

        # How strict the latex detector is for automatic compilation
        self.autotex_level = None  # type: AutoTexLevel

        # Whether the automatic latex detector only reads codeblocks
        self.require_codeblocks = None  # type: bool

        # The list of channels the automatic latex detector reads. If None, read all channels.
        self.latex_channels = None  # type: List[int]

        # The default preamble used when compiling latex in this guild
        self.preamble = None  # type: str

        # Load values from database
        self.load()

    def load(self):
        """
        Retrieve the guild data from the database, handling the DM context (id 0) separately
        """
        if self.id == 0:
            self.autotex = True
            self.autotex_level = AutoTexLevel.WEAK
            self.require_codeblocks = False
            self.latex_channels = None
            self.preamble = None
            return

        # Set defaults
        for attr, value in self.defaults.items():
            setattr(self, attr, value)

        # Get base config
        rows = self._client.data.guild_latex_config.select_where(guildid=self.id)
        if rows:
            row = rows[0]
            if row["autotex"] is not None:
                self.autotex = row["autotex"]  # type: bool

            if row["autotex_level"] is not None:
                self.autotex_level = AutoTexLevel(row["autotex_level"])

            if row["require_codeblocks"] is not None:
                self.require_codeblocks = row["require_codeblocks"]

        # Get latex channels
        rows = self._client.data.guild_latex_channels.select_where(guildid=self.id)
        if rows:
            self.latex_channels = [row['channelid'] for row in rows]

        # Get preamble
        rows = self._client.data.guild_latex_preambles.select_where(guildid=self.id)
        if rows:
            self.preamble = rows[0]['preamble'] or self.preamble

    @classmethod
    def get(cls, id):
        if id not in cls.cached_guilds:
            cls.cached_guilds[id] = cls(id)
        return cls.cached_guilds[id]


module.LatexGuild = LatexGuild


@module.data_init_task
def attach_latexguild_client(client):
    LatexGuild._client = client
