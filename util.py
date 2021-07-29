class Generic:
    """Generic class used as basis for attribute-based structures."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
