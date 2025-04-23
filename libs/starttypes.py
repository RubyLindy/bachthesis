class StartError(Exception):
    """Uuuuuhh don't know what this should be yet"""
    pass


class text:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value