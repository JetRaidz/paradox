class Interface:
    """
    Abstract base class representing a data interface.
    """
    _schema = None

    @property
    def schema(self):
        return self._schema
